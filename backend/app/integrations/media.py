from __future__ import annotations

import base64
import io
import json
import math
import wave
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4////fwAJ+wP9KobjigAAAABJRU5ErkJggg=="
)


@dataclass
class GeneratedMedia:
    provider_name: str
    provider_model: str
    content_type: str
    file_extension: str
    bytes_payload: bytes
    metadata: dict[str, Any]


class ImageProvider:
    def generate_frame(
        self,
        *,
        prompt: str,
        scene_index: int,
        frame_kind: str,
        reference_asset_id: str | None,
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
        start_frame_asset_id: str,
        end_frame_asset_id: str,
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
    sample_rate = 16000
    sample_count = max(1, int(duration_seconds * sample_rate))
    amplitude = 12000
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
        reference_asset_id: str | None,
        consistency_pack_state: dict[str, Any] | None,
    ) -> GeneratedMedia:
        return GeneratedMedia(
            provider_name=self.provider_name,
            provider_model=self.provider_model,
            content_type="image/png",
            file_extension="png",
            bytes_payload=PNG_1X1,
            metadata={
                "scene_index": scene_index,
                "frame_kind": frame_kind,
                "prompt": prompt,
                "reference_asset_id": reference_asset_id,
                "consistency_pack_state": consistency_pack_state or {},
                "width": 1080,
                "height": 1920,
            },
        )


class StubVideoProvider(VideoProvider):
    def __init__(self, *, provider_name: str = "stub_video_provider", provider_model: str = "stub-video-v1") -> None:
        self.provider_name = provider_name
        self.provider_model = provider_model

    def generate_clip(
        self,
        *,
        prompt: str,
        scene_index: int,
        duration_seconds: int,
        start_frame_asset_id: str,
        end_frame_asset_id: str,
    ) -> GeneratedMedia:
        payload = {
            "scene_index": scene_index,
            "prompt": prompt,
            "duration_seconds": duration_seconds,
            "start_frame_asset_id": start_frame_asset_id,
            "end_frame_asset_id": end_frame_asset_id,
            "generation_mode": "first_last_frame_stub",
        }
        return GeneratedMedia(
            provider_name=self.provider_name,
            provider_model=self.provider_model,
            content_type="application/json",
            file_extension="json",
            bytes_payload=json.dumps(payload, indent=2).encode("utf-8"),
            metadata={
                **payload,
                "has_audio_stream": True,
                "width": 1080,
                "height": 1920,
                "frame_rate": 24.0,
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


class StubMusicProvider(MusicProvider):
    def prepare_track(self, *, total_duration_seconds: int) -> GeneratedMedia:
        wav_bytes = _sine_wave_wav(max(1.0, float(total_duration_seconds)), frequency=110.0)
        return GeneratedMedia(
            provider_name="stub_music_provider",
            provider_model="stub-music-library-v1",
            content_type="audio/wav",
            file_extension="wav",
            bytes_payload=wav_bytes,
            metadata={
                "duration_ms": int(max(1.0, float(total_duration_seconds)) * 1000),
                "track_name": "default-curated-track",
                "license": "royalty_free_stub",
            },
        )


def build_image_provider(settings: Settings) -> ImageProvider:
    del settings
    return StubImageProvider()


def build_video_provider(settings: Settings) -> VideoProvider:
    del settings
    return StubVideoProvider()


def build_speech_provider(settings: Settings) -> SpeechProvider:
    del settings
    return StubSpeechProvider()


def build_music_provider(settings: Settings) -> MusicProvider:
    del settings
    return StubMusicProvider()
