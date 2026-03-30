from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import re

import httpx
from PIL import Image, ImageDraw

from app.core.config import Settings, get_settings
from app.core.errors import AdapterError
from app.integrations.ffmpeg import FFmpegError, FFmpegRunner


def _normalize_azure_endpoint(raw_endpoint: str) -> str:
    """Normalize an Azure endpoint to just scheme://host.

    Users often paste the full curl URL from Azure docs (including
    /openai/deployments/…/images/generations?api-version=…) into the
    endpoint field.  Strip the path *and* query string so the code can
    append the correct path later without doubling it.
    """
    from urllib.parse import urlparse

    endpoint = raw_endpoint.strip().rstrip("/")
    parsed = urlparse(endpoint)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        path_q = f"{parsed.path or ''}?{parsed.query or ''}".lower()
        if "/openai/" in path_q:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        if parsed.path and parsed.path != "/":
            match = re.match(
                r"(https?://[^/]+)(/openai/.*)$",
                endpoint,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).rstrip("/")
    return endpoint.rstrip("/")


def _normalize_azure_api_version(raw: str | None) -> str:
    """Strip accidental repeated ``api-version=`` prefixes from config or env."""
    if not raw:
        return ""
    version = str(raw).strip().lstrip("?")
    prefix = "api-version="
    while version.lower().startswith(prefix):
        version = version[len(prefix):].strip()
    return version.strip()


@dataclass
class GeneratedMedia:
    provider_name: str
    provider_model: str
    content_type: str
    file_extension: str
    bytes_payload: bytes
    metadata: dict[str, Any]


@dataclass
class ImageReference:
    asset_id: str | None
    content_type: str
    bytes_payload: bytes
    role: str = "reference"


class ImageProvider:
    def generate_frame(
        self,
        *,
        prompt: str,
        scene_index: int,
        frame_kind: str,
        reference_images: list[ImageReference],
        consistency_pack_state: dict[str, Any] | None,
    ) -> GeneratedMedia:  # pragma: no cover - interface
        raise NotImplementedError


class VideoProvider:
    def generate_clip(
        self,
        *,
        prompt: str,
        scene_index: int,
        duration_seconds: int,
        start_frame_bytes: bytes,
        start_frame_content_type: str,
        end_frame_bytes: bytes,
        end_frame_content_type: str,
    ) -> GeneratedMedia:  # pragma: no cover - interface
        raise NotImplementedError


class SpeechProvider:
    def synthesize(
        self,
        *,
        text: str,
        scene_index: int,
        voice_preset: dict[str, Any] | None,
    ) -> GeneratedMedia:  # pragma: no cover - interface
        raise NotImplementedError


class MusicProvider:
    def prepare_track(
        self,
        *,
        total_duration_seconds: int,
    ) -> GeneratedMedia:  # pragma: no cover - interface
        raise NotImplementedError


def _sine_wave_wav(duration_seconds: float, *, frequency: float = 220.0) -> bytes:
    sample_rate = 24000
    sample_count = max(1, int(duration_seconds * sample_rate))
    amplitude = 10000
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for sample_index in range(sample_count):
            t = sample_index / sample_rate
            value = int(amplitude * math.sin(2 * math.pi * frequency * t))
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(frames))
    return buffer.getvalue()


def _prompt_color(prompt: str, frame_kind: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(f"{prompt}|{frame_kind}".encode("utf-8")).digest()
    return digest[0], digest[1], digest[2]


def _png_from_prompt(
    *,
    prompt: str,
    frame_kind: str,
    scene_index: int,
    reference_images: list[ImageReference],
) -> bytes:
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), color=_prompt_color(prompt, frame_kind))
    draw = ImageDraw.Draw(image)
    accent = (255, 255, 255)
    draw.rectangle((80, 80, width - 80, height - 80), outline=accent, width=8)
    draw.rectangle((120, 120, width - 120, 420), fill=(0, 0, 0))
    text = (
        f"Scene {scene_index:02d} {frame_kind.upper()}\n"
        f"Refs: {len(reference_images)}\n\n"
        f"{prompt[:180]}"
    )
    draw.multiline_text((150, 160), text, fill=accent, spacing=10)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _normalize_image_for_video(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    target_ratio = 1080 / 1920
    current_ratio = width / max(height, 1)
    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        offset = max(0, (width - new_width) // 2)
        image = image.crop((offset, 0, offset + new_width, height))
    else:
        new_height = int(width / target_ratio)
        offset = max(0, (height - new_height) // 2)
        image = image.crop((0, offset, width, offset + new_height))
    image = image.resize((1080, 1920))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _fallback_video_bytes(
    *,
    settings: Settings,
    start_frame_bytes: bytes,
    end_frame_bytes: bytes,
    duration_seconds: int,
) -> tuple[bytes, dict[str, Any]]:
    runner = FFmpegRunner(settings)
    if not runner.available():
        payload = {
            "duration_seconds": duration_seconds,
            "generation_mode": "first_last_frame_manifest_fallback",
        }
        return json.dumps(payload, indent=2).encode("utf-8"), {
            **payload,
            "has_audio_stream": False,
            "width": 1080,
            "height": 1920,
            "frame_rate": 24.0,
            "continuity_mode": "first_last_frame_fallback",
            "fallback_format": "json",
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        (workdir / "start.png").write_bytes(_normalize_image_for_video(start_frame_bytes))
        (workdir / "end.png").write_bytes(_normalize_image_for_video(end_frame_bytes))
        transition_duration = min(0.6, max(0.2, duration_seconds / 6))
        transition_offset = max(0.0, duration_seconds - transition_duration)
        runner.run(
            "ffmpeg",
            [
                "-y",
                "-loop",
                "1",
                "-t",
                str(duration_seconds),
                "-i",
                "start.png",
                "-loop",
                "1",
                "-t",
                str(duration_seconds),
                "-i",
                "end.png",
                "-filter_complex",
                (
                    "[0:v]scale=1080:1920,setsar=1[v0];"
                    "[1:v]scale=1080:1920,setsar=1[v1];"
                    f"[v0][v1]xfade=transition=fade:duration={transition_duration}:"
                    f"offset={transition_offset},format=yuv420p[v]"
                ),
                "-map",
                "[v]",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "out.mp4",
            ],
            workdir=workdir,
        )
        metadata = runner.probe("out.mp4", workdir=workdir)
        stream = next(
            (
                item
                for item in metadata.get("streams", [])
                if item.get("codec_type") == "video"
            ),
            {},
        )
        format_payload = metadata.get("format", {})
        duration_ms = int(float(format_payload.get("duration") or duration_seconds) * 1000)
        return (workdir / "out.mp4").read_bytes(), {
            "duration_ms": duration_ms,
            "has_audio_stream": False,
            "width": int(stream.get("width") or 1080),
            "height": int(stream.get("height") or 1920),
            "frame_rate": 24.0,
            "continuity_mode": "first_last_frame_fallback",
        }


class StubImageProvider(ImageProvider):
    def __init__(self, *, provider_name: str = "stub_image_provider", provider_model: str = "stub-image-v1") -> None:
        self.provider_name = provider_name
        self.provider_model = provider_model

    def generate_frame(
        self,
        *,
        prompt: str,
        scene_index: int,
        frame_kind: str,
        reference_images: list[ImageReference],
        consistency_pack_state: dict[str, Any] | None,
    ) -> GeneratedMedia:
        return GeneratedMedia(
            provider_name=self.provider_name,
            provider_model=self.provider_model,
            content_type="image/png",
            file_extension="png",
            bytes_payload=_png_from_prompt(
                prompt=prompt,
                frame_kind=frame_kind,
                scene_index=scene_index,
                reference_images=reference_images,
            ),
            metadata={
                "scene_index": scene_index,
                "frame_kind": frame_kind,
                "prompt": prompt,
                "reference_asset_ids": [reference.asset_id for reference in reference_images],
                "consistency_pack_state": consistency_pack_state or {},
                "width": 1080,
                "height": 1920,
            },
        )


class AzureOpenAIImageProvider(ImageProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
    ) -> None:
        self.settings = settings
        self.endpoint = _normalize_azure_endpoint(endpoint or settings.azure_openai_endpoint or "")
        self.api_key = api_key or settings.azure_openai_api_key
        self.deployment = deployment or settings.azure_openai_image_deployment
        self.api_version = _normalize_azure_api_version(
            api_version or settings.azure_openai_image_api_version or ""
        ) or (settings.azure_openai_image_api_version or "")
        self.model = model or settings.azure_openai_image_model

    def _fallback_generated_media(
        self,
        *,
        prompt: str,
        scene_index: int,
        frame_kind: str,
        reference_images: list[ImageReference],
        consistency_pack_state: dict[str, Any] | None,
    ) -> GeneratedMedia:
        generated = StubImageProvider(
            provider_name="azure_openai_image",
            provider_model=self.deployment or self.model,
        ).generate_frame(
            prompt=prompt,
            scene_index=scene_index,
            frame_kind=frame_kind,
            reference_images=reference_images,
            consistency_pack_state=consistency_pack_state,
        )
        generated.metadata["fallback_mode"] = "local_placeholder"
        return generated

    def generate_frame(
        self,
        *,
        prompt: str,
        scene_index: int,
        frame_kind: str,
        reference_images: list[ImageReference],
        consistency_pack_state: dict[str, Any] | None,
    ) -> GeneratedMedia:
        if not self.endpoint or not self.api_key or not self.deployment:
            return self._fallback_generated_media(
                prompt=prompt,
                scene_index=scene_index,
                frame_kind=frame_kind,
                reference_images=reference_images,
                consistency_pack_state=consistency_pack_state,
            )

        headers = {"api-key": self.api_key, "Authorization": f"Bearer {self.api_key}"}
        try:
            if reference_images:
                url = (
                    f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}/images/edits"
                    f"?api-version={self.api_version}"
                )
                files = [
                    (
                        "image",
                        (
                            f"reference-{index + 1}.png",
                            reference.bytes_payload,
                            reference.content_type,
                        ),
                    )
                    for index, reference in enumerate(reference_images[:1])
                ]
                response = httpx.post(
                    url,
                    headers=headers,
                    data={
                        "prompt": prompt,
                        "model": self.model,
                        "size": "1024x1024",
                        "n": "1",
                        "quality": "high",
                    },
                    files=files,
                    timeout=90.0,
                )
            else:
                url = (
                    f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}/images/generations"
                    f"?api-version={self.api_version}"
                )
                response = httpx.post(
                    url,
                    headers={**headers, "Content-Type": "application/json"},
                    json={
                        "prompt": prompt,
                        "model": self.model,
                        "size": "1024x1024",
                        "n": 1,
                        "quality": "high",
                    },
                    timeout=90.0,
                )
            if response.status_code >= 500:
                raise AdapterError(
                    "transient",
                    "azure_image_generation_unavailable",
                    "Azure image generation is temporarily unavailable.",
                )
            if response.status_code >= 400:
                raise AdapterError(
                    "deterministic_input",
                    "azure_image_generation_rejected",
                    response.text,
                )
            payload = response.json()
            image_b64 = (((payload.get("data") or [{}])[0]).get("b64_json")) or ""
            if not image_b64:
                raise AdapterError(
                    "internal",
                    "azure_image_generation_empty",
                    "Azure image generation returned no image payload.",
                )
            image_bytes = base64.b64decode(image_b64)
            return GeneratedMedia(
                provider_name="azure_openai_image",
                provider_model=self.deployment,
                content_type="image/png",
                file_extension="png",
                bytes_payload=image_bytes,
                metadata={
                    "scene_index": scene_index,
                    "frame_kind": frame_kind,
                    "prompt": prompt,
                    "reference_asset_ids": [reference.asset_id for reference in reference_images],
                    "consistency_pack_state": consistency_pack_state or {},
                    "width": 1024,
                    "height": 1024,
                },
            )
        except httpx.TimeoutException as exc:
            raise AdapterError("transient", "azure_image_generation_timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise AdapterError("transient", "azure_image_generation_http_error", str(exc)) from exc


class StubVideoProvider(VideoProvider):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        provider_name: str = "stub_video_provider",
        provider_model: str = "stub-video-v1",
    ) -> None:
        self.settings = settings or get_settings()
        self.provider_name = provider_name
        self.provider_model = provider_model

    def generate_clip(
        self,
        *,
        prompt: str,
        scene_index: int,
        duration_seconds: int,
        start_frame_bytes: bytes,
        start_frame_content_type: str,
        end_frame_bytes: bytes,
        end_frame_content_type: str,
    ) -> GeneratedMedia:
        del start_frame_content_type, end_frame_content_type
        video_bytes, metadata = _fallback_video_bytes(
            settings=self.settings,
            start_frame_bytes=start_frame_bytes,
            end_frame_bytes=end_frame_bytes,
            duration_seconds=duration_seconds,
        )
        content_type = "video/mp4" if metadata.get("fallback_format") != "json" else "application/json"
        extension = "mp4" if content_type == "video/mp4" else "json"
        return GeneratedMedia(
            provider_name=self.provider_name,
            provider_model=self.provider_model,
            content_type=content_type,
            file_extension=extension,
            bytes_payload=video_bytes,
            metadata={
                **metadata,
                "scene_index": scene_index,
                "prompt": prompt,
                "generation_mode": "first_last_frame_stub",
            },
        )


class VeoVideoProvider(VideoProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_clip(
        self,
        *,
        prompt: str,
        scene_index: int,
        duration_seconds: int,
        start_frame_bytes: bytes,
        start_frame_content_type: str,
        end_frame_bytes: bytes,
        end_frame_content_type: str,
    ) -> GeneratedMedia:
        del start_frame_content_type, end_frame_content_type
        video_bytes, metadata = _fallback_video_bytes(
            settings=self.settings,
            start_frame_bytes=start_frame_bytes,
            end_frame_bytes=end_frame_bytes,
            duration_seconds=duration_seconds,
        )
        content_type = "video/mp4" if metadata.get("fallback_format") != "json" else "application/json"
        extension = "mp4" if content_type == "video/mp4" else "json"
        return GeneratedMedia(
            provider_name="veo_video",
            provider_model=self.settings.vertex_ai_model_id,
            content_type=content_type,
            file_extension=extension,
            bytes_payload=video_bytes,
            metadata={
                **metadata,
                "scene_index": scene_index,
                "prompt": prompt,
                "generation_mode": "first_last_frame_video",
                "provider_path": "ffmpeg_fallback"
                if metadata.get("fallback_format")
                else "local_ffmpeg",
            },
        )


class StubSpeechProvider(SpeechProvider):
    def __init__(self, *, provider_name: str = "stub_speech_provider", provider_model: str = "stub-speech-v1") -> None:
        self.provider_name = provider_name
        self.provider_model = provider_model

    def synthesize(
        self,
        *,
        text: str,
        scene_index: int,
        voice_preset: dict[str, Any] | None,
    ) -> GeneratedMedia:
        word_count = max(1, len(text.split()))
        duration_seconds = max(1.0, word_count / 2.4)
        frequency = 220.0 + (scene_index * 20)
        wav_bytes = _sine_wave_wav(duration_seconds, frequency=frequency)
        return GeneratedMedia(
            provider_name=self.provider_name,
            provider_model=self.provider_model,
            content_type="audio/wav",
            file_extension="wav",
            bytes_payload=wav_bytes,
            metadata={
                "scene_index": scene_index,
                "text": text,
                "voice_preset": voice_preset or {},
                "duration_ms": int(duration_seconds * 1000),
                "language_code": (voice_preset or {}).get("language_code", "en-US"),
            },
        )


class AzureOpenAISpeechProvider(SpeechProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
        default_voice: str | None = None,
    ) -> None:
        self.settings = settings
        self.endpoint = _normalize_azure_endpoint(endpoint or settings.azure_openai_endpoint or "")
        self.api_key = api_key or settings.azure_openai_api_key
        self.deployment = deployment or settings.azure_openai_speech_deployment
        self.api_version = _normalize_azure_api_version(
            api_version or settings.azure_openai_speech_api_version or ""
        ) or (settings.azure_openai_speech_api_version or "")
        self.model = model or settings.azure_openai_speech_model
        self.default_voice = default_voice or settings.azure_openai_speech_voice

    def synthesize(
        self,
        *,
        text: str,
        scene_index: int,
        voice_preset: dict[str, Any] | None,
    ) -> GeneratedMedia:
        if not self.endpoint or not self.api_key or not self.deployment:
            generated = StubSpeechProvider(
                provider_name="azure_openai_speech",
                provider_model=self.deployment or self.model,
            ).synthesize(text=text, scene_index=scene_index, voice_preset=voice_preset)
            generated.metadata["fallback_mode"] = "local_placeholder"
            return generated

        voice = str((voice_preset or {}).get("provider_voice") or self.default_voice)
        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}/audio/speech"
            f"?api-version={self.api_version}"
        )
        try:
            response = httpx.post(
                url,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": text,
                    "voice": voice,
                },
                timeout=90.0,
            )
            if response.status_code >= 500:
                raise AdapterError(
                    "transient",
                    "azure_speech_unavailable",
                    "Azure speech generation is temporarily unavailable.",
                )
            if response.status_code >= 400:
                raise AdapterError("deterministic_input", "azure_speech_rejected", response.text)
            return GeneratedMedia(
                provider_name="azure_openai_speech",
                provider_model=self.deployment,
                content_type="audio/mpeg",
                file_extension="mp3",
                bytes_payload=response.content,
                metadata={
                    "scene_index": scene_index,
                    "text": text,
                    "voice_preset": voice_preset or {},
                    "language_code": (voice_preset or {}).get("language_code", "en-US"),
                },
            )
        except httpx.TimeoutException as exc:
            raise AdapterError("transient", "azure_speech_timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise AdapterError("transient", "azure_speech_http_error", str(exc)) from exc


class CuratedMusicProvider(MusicProvider):
    def prepare_track(self, *, total_duration_seconds: int) -> GeneratedMedia:
        wav_bytes = _sine_wave_wav(max(1.0, float(total_duration_seconds)), frequency=110.0)
        return GeneratedMedia(
            provider_name="curated_music_library",
            provider_model="royalty-free-pack-1",
            content_type="audio/wav",
            file_extension="wav",
            bytes_payload=wav_bytes,
            metadata={
                "duration_ms": int(max(1.0, float(total_duration_seconds)) * 1000),
                "track_name": "royalty-free-bed-a",
                "license": "royalty_free_curated",
            },
        )


def build_image_provider(settings: Settings) -> ImageProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubImageProvider()
    return AzureOpenAIImageProvider(settings)


def build_video_provider(settings: Settings) -> VideoProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubVideoProvider(settings=settings)
    return VeoVideoProvider(settings)


def build_speech_provider(settings: Settings) -> SpeechProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubSpeechProvider()
    return AzureOpenAISpeechProvider(settings)


def build_music_provider(settings: Settings) -> MusicProvider:
    del settings
    return CuratedMusicProvider()

