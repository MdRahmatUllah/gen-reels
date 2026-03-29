from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import AdapterError
from app.integrations.media import (
    GeneratedMedia,
    ImageProvider,
    ImageReference,
    SpeechProvider,
    StubImageProvider,
    StubSpeechProvider,
    StubVideoProvider,
    VideoProvider,
)

STABILITY_API_BASE_URL = "https://api.stability.ai"
ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io"
RUNWAY_API_BASE_URL = "https://api.dev.runwayml.com"
RUNWAY_API_VERSION = "2024-11-06"


def _image_data_uri(content_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    media_type = content_type or "image/png"
    return f"data:{media_type};base64,{encoded}"


class StabilityImageProvider(ImageProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        model: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self.settings = settings
        self.api_key = api_key or ""
        self.model = model or "stable-image-core"
        self.endpoint = (endpoint or STABILITY_API_BASE_URL).rstrip("/")

    def _operation_path(self) -> str:
        lowered = self.model.lower()
        if "ultra" in lowered:
            return "/v2beta/stable-image/generate/ultra"
        return "/v2beta/stable-image/generate/core"

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
            provider_name="stability_image",
            provider_model=self.model,
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
        if not self.api_key:
            return self._fallback_generated_media(
                prompt=prompt,
                scene_index=scene_index,
                frame_kind=frame_kind,
                reference_images=reference_images,
                consistency_pack_state=consistency_pack_state,
            )

        try:
            response = httpx.post(
                f"{self.endpoint}{self._operation_path()}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/*",
                },
                data={
                    "prompt": prompt,
                    "aspect_ratio": "9:16",
                    "output_format": "png",
                },
                timeout=90.0,
            )
        except httpx.TimeoutException as exc:
            raise AdapterError("transient", "stability_image_timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise AdapterError("transient", "stability_image_http_error", str(exc)) from exc

        if response.status_code >= 500:
            raise AdapterError(
                "transient",
                "stability_image_unavailable",
                "Stability AI image generation is temporarily unavailable.",
            )
        if response.status_code >= 400:
            raise AdapterError("deterministic_input", "stability_image_rejected", response.text)

        content_type = response.headers.get("Content-Type", "image/png").split(";")[0].strip() or "image/png"
        file_extension = "png" if "png" in content_type else "jpg" if "jpeg" in content_type else "webp"
        return GeneratedMedia(
            provider_name="stability_image",
            provider_model=self.model,
            content_type=content_type,
            file_extension=file_extension,
            bytes_payload=response.content,
            metadata={
                "scene_index": scene_index,
                "frame_kind": frame_kind,
                "prompt": prompt,
                "reference_asset_ids": [reference.asset_id for reference in reference_images],
                "consistency_pack_state": consistency_pack_state or {},
                "reference_inputs_supported": False,
            },
        )


class ElevenLabsSpeechProvider(SpeechProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        model: str | None = None,
        voice: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self.settings = settings
        self.api_key = api_key or ""
        self.model = model or "eleven_multilingual_v2"
        self.voice = voice or ""
        self.endpoint = (endpoint or ELEVENLABS_API_BASE_URL).rstrip("/")

    def synthesize(
        self,
        *,
        text: str,
        scene_index: int,
        voice_preset: dict[str, Any] | None,
    ) -> GeneratedMedia:
        if not self.api_key or not self.voice:
            generated = StubSpeechProvider(
                provider_name="elevenlabs_speech",
                provider_model=self.model,
            ).synthesize(text=text, scene_index=scene_index, voice_preset=voice_preset)
            generated.metadata["fallback_mode"] = "local_placeholder"
            return generated

        try:
            response = httpx.post(
                f"{self.endpoint}/v1/text-to-speech/{self.voice}",
                headers={
                    "xi-api-key": self.api_key,
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": self.model,
                    "output_format": "mp3_44100_128",
                },
                timeout=90.0,
            )
        except httpx.TimeoutException as exc:
            raise AdapterError("transient", "elevenlabs_timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise AdapterError("transient", "elevenlabs_http_error", str(exc)) from exc

        if response.status_code >= 500:
            raise AdapterError(
                "transient",
                "elevenlabs_unavailable",
                "ElevenLabs speech generation is temporarily unavailable.",
            )
        if response.status_code >= 400:
            raise AdapterError("deterministic_input", "elevenlabs_rejected", response.text)

        return GeneratedMedia(
            provider_name="elevenlabs_speech",
            provider_model=self.model,
            content_type="audio/mpeg",
            file_extension="mp3",
            bytes_payload=response.content,
            metadata={
                "scene_index": scene_index,
                "text": text,
                "voice_preset": voice_preset or {},
                "language_code": (voice_preset or {}).get("language_code", "en-US"),
                "provider_voice": self.voice,
            },
        )


class RunwayVideoProvider(VideoProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        model: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self.settings = settings
        self.api_key = api_key or ""
        self.model = model or "gen4_turbo"
        self.endpoint = (endpoint or RUNWAY_API_BASE_URL).rstrip("/")

    def _request_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": RUNWAY_API_VERSION,
        }

    def _poll_task(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + 180.0
        last_payload: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get(
                    f"{self.endpoint}/v1/tasks/{task_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "X-Runway-Version": RUNWAY_API_VERSION,
                    },
                    timeout=30.0,
                )
            except httpx.TimeoutException as exc:
                raise AdapterError("transient", "runway_task_timeout", str(exc)) from exc
            except httpx.HTTPError as exc:
                raise AdapterError("transient", "runway_task_http_error", str(exc)) from exc

            if response.status_code >= 500:
                raise AdapterError(
                    "transient",
                    "runway_task_unavailable",
                    "Runway task retrieval is temporarily unavailable.",
                )
            if response.status_code >= 400:
                raise AdapterError("deterministic_input", "runway_task_rejected", response.text)

            payload = response.json()
            last_payload = payload
            status = str(payload.get("status") or "").upper()
            if status == "SUCCEEDED":
                return payload
            if status in {"FAILED", "CANCELED"}:
                failure = str(payload.get("failure") or payload.get("failureCode") or "Runway task failed.")
                raise AdapterError("deterministic_input", "runway_task_failed", failure)
            time.sleep(5.0)

        raise AdapterError(
            "transient",
            "runway_task_timeout",
            f"Runway video generation did not complete before timeout. Last status: {last_payload.get('status') if last_payload else 'unknown'}.",
        )

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
        if not self.api_key:
            generated = StubVideoProvider(
                settings=self.settings,
                provider_name="runway_video",
                provider_model=self.model,
            ).generate_clip(
                prompt=prompt,
                scene_index=scene_index,
                duration_seconds=duration_seconds,
                start_frame_bytes=start_frame_bytes,
                start_frame_content_type=start_frame_content_type,
                end_frame_bytes=end_frame_bytes,
                end_frame_content_type=end_frame_content_type,
            )
            generated.metadata["fallback_mode"] = "local_placeholder"
            return generated

        resolved_duration = 5 if duration_seconds <= 5 else 10
        try:
            response = httpx.post(
                f"{self.endpoint}/v1/image_to_video",
                headers=self._request_headers(),
                json={
                    "model": self.model,
                    "promptText": prompt[:1000],
                    "promptImage": [
                        {
                            "uri": _image_data_uri(start_frame_content_type, start_frame_bytes),
                            "position": "first",
                        },
                        {
                            "uri": _image_data_uri(end_frame_content_type, end_frame_bytes),
                            "position": "last",
                        },
                    ],
                    "ratio": "720:1280",
                    "duration": resolved_duration,
                },
                timeout=60.0,
            )
        except httpx.TimeoutException as exc:
            raise AdapterError("transient", "runway_video_timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise AdapterError("transient", "runway_video_http_error", str(exc)) from exc

        if response.status_code >= 500:
            raise AdapterError(
                "transient",
                "runway_video_unavailable",
                "Runway video generation is temporarily unavailable.",
            )
        if response.status_code >= 400:
            raise AdapterError("deterministic_input", "runway_video_rejected", response.text)

        task_id = str(response.json().get("id") or "").strip()
        if not task_id:
            raise AdapterError("internal", "runway_task_missing", "Runway did not return a task ID.")

        task_payload = self._poll_task(task_id)
        output_urls = task_payload.get("output") or []
        if not output_urls:
            raise AdapterError("internal", "runway_output_missing", "Runway task completed without a video output.")

        video_url = str(output_urls[0])
        try:
            media_response = httpx.get(video_url, timeout=90.0)
        except httpx.TimeoutException as exc:
            raise AdapterError("transient", "runway_output_timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise AdapterError("transient", "runway_output_http_error", str(exc)) from exc

        if media_response.status_code >= 500:
            raise AdapterError(
                "transient",
                "runway_output_unavailable",
                "Runway video output download is temporarily unavailable.",
            )
        if media_response.status_code >= 400:
            raise AdapterError("deterministic_input", "runway_output_rejected", media_response.text)

        return GeneratedMedia(
            provider_name="runway_video",
            provider_model=self.model,
            content_type="video/mp4",
            file_extension="mp4",
            bytes_payload=media_response.content,
            metadata={
                "scene_index": scene_index,
                "prompt": prompt,
                "duration_ms": resolved_duration * 1000,
                "continuity_mode": "first_last_frame",
                "generation_mode": "runway_image_to_video",
                "provider_task_id": task_id,
                "provider_output_url": video_url,
            },
        )
