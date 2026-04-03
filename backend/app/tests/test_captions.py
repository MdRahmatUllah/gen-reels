from __future__ import annotations

import sys
import types

from app.core.config import Settings
from app.integrations import captions


def test_whisper_device_candidates_prefers_cuda_when_available(monkeypatch):
    settings = Settings(environment="test", faster_whisper_device="auto")
    monkeypatch.setattr(captions, "_detect_cuda_available", lambda: True)

    assert captions._whisper_device_candidates(settings) == ["cuda", "cpu"]


def test_whisper_device_candidates_honors_cpu_override():
    settings = Settings(environment="test", faster_whisper_device="cpu")

    assert captions._whisper_device_candidates(settings) == ["cpu"]


def test_whisper_cache_dir_uses_settings_and_creates_directory(tmp_path):
    cache_dir = tmp_path / "fw-cache"
    settings = Settings(environment="test", faster_whisper_cache_dir=str(cache_dir))

    resolved = captions._whisper_cache_dir(settings)

    assert resolved == str(cache_dir)
    assert cache_dir.exists()


def test_load_whisper_model_is_cached(monkeypatch, tmp_path):
    captions._load_whisper_model.cache_clear()

    created: list[tuple[str, str, str, str]] = []

    class FakeWhisperModel:
        def __init__(self, model_size: str, *, device: str, compute_type: str, download_root: str):
            created.append((model_size, device, compute_type, download_root))

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    first = captions._load_whisper_model("small", "cpu", "int8", str(tmp_path))
    second = captions._load_whisper_model("small", "cpu", "int8", str(tmp_path))

    assert first is second
    assert created == [("small", "cpu", "int8", str(tmp_path))]
