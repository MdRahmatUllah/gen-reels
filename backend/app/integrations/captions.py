"""Viral-style caption burning using faster-whisper + ASS subtitles.

Used by three pipelines:
- Remix videos (burn_captions)
- Project render pipeline (_generate_ass_from_narration_bytes)
- Series (caption_style_key → style preset)

Pipeline:
1. Transcribe audio with faster-whisper (word-level timestamps)
2. Generate ASS subtitle file with per-word karaoke \\kf highlight
3. Burn via FFmpeg's ass= filter (preserves all styling)
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from app.integrations.ffmpeg import FFmpegRunner

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


# ── Style presets ──────────────────────────────────────────────────────────────

CAPTION_STYLES: dict[str, dict] = {
    # Classic CapCut / TikTok — white bold, gold active-word highlight
    "capcut": {
        "font_name": "Liberation Sans",
        "font_size": 90,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000D4FF",  # gold
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "bold": 1,
        "outline": 5,
        "shadow": 2,
        "uppercase": True,
        "words_per_group": 1,
        "margin_v": 120,
    },
    # Mr. Beast — bright yellow highlight, extra heavy stroke
    "mrbeast": {
        "font_name": "Liberation Sans",
        "font_size": 100,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000E6FF",  # bright yellow
        "outline_color": "&H00000000",
        "shadow_color": "&HAA000000",
        "bold": 1,
        "outline": 6,
        "shadow": 2,
        "uppercase": True,
        "words_per_group": 1,
        "margin_v": 110,
    },
    # Clean subtitle box — multi-word phrases, lower opacity background
    "subtitle": {
        "font_name": "Liberation Sans",
        "font_size": 72,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "bold": 0,
        "outline": 4,
        "shadow": 1,
        "uppercase": False,
        "words_per_group": 5,
        "margin_v": 100,
    },
    # Neon / cyber — cyan text, hot-pink highlight
    "neon": {
        "font_name": "Liberation Sans",
        "font_size": 88,
        "primary_color": "&H00C8FF00",
        "secondary_color": "&H00963296",  # hot pink
        "outline_color": "&H00507864",
        "shadow_color": "&H7800C8FF",
        "bold": 1,
        "outline": 5,
        "shadow": 2,
        "uppercase": True,
        "words_per_group": 2,
        "margin_v": 120,
    },
    # Minimal — clean, readable, not too large
    "minimal": {
        "font_name": "Liberation Sans",
        "font_size": 64,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "shadow_color": "&H00000000",
        "bold": 0,
        "outline": 3,
        "shadow": 1,
        "uppercase": False,
        "words_per_group": 4,
        "margin_v": 100,
    },
    # Bold stroke — heavy outline, very readable
    "bold_stroke": {
        "font_name": "Liberation Sans",
        "font_size": 96,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000FFFF",  # yellow
        "outline_color": "&H00000000",
        "shadow_color": "&HAA000000",
        "bold": 1,
        "outline": 7,
        "shadow": 2,
        "uppercase": True,
        "words_per_group": 1,
        "margin_v": 115,
    },
    # Red highlight — white base, red active word (dramatic/news style)
    "red_highlight": {
        "font_name": "Liberation Sans",
        "font_size": 88,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H000000FF",  # red in BGR
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "bold": 1,
        "outline": 5,
        "shadow": 2,
        "uppercase": True,
        "words_per_group": 1,
        "margin_v": 120,
    },
    # Sleek — modern, clean, multi-word
    "sleek": {
        "font_name": "Liberation Sans",
        "font_size": 72,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00AAAAAA",
        "outline_color": "&H00000000",
        "shadow_color": "&H60000000",
        "bold": 0,
        "outline": 3,
        "shadow": 1,
        "uppercase": False,
        "words_per_group": 3,
        "margin_v": 110,
    },
    # Karaoke — word-by-word, colour shifts
    "karaoke": {
        "font_name": "Liberation Sans",
        "font_size": 86,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00FF8000",  # orange
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "bold": 1,
        "outline": 5,
        "shadow": 2,
        "uppercase": False,
        "words_per_group": 1,
        "margin_v": 120,
    },
    # Majestic — cinematic, dramatic caps
    "majestic": {
        "font_name": "Liberation Sans",
        "font_size": 92,
        "primary_color": "&H00FFD700",  # gold text
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "shadow_color": "&HCC000000",
        "bold": 1,
        "outline": 6,
        "shadow": 3,
        "uppercase": True,
        "words_per_group": 2,
        "margin_v": 115,
    },
    # Beast — punchy high-energy (alias of mrbeast)
    "beast": {
        "font_name": "Liberation Sans",
        "font_size": 104,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000E6FF",
        "outline_color": "&H00000000",
        "shadow_color": "&HCC000000",
        "bold": 1,
        "outline": 7,
        "shadow": 2,
        "uppercase": True,
        "words_per_group": 1,
        "margin_v": 110,
    },
    # Elegant — refined, lowercase, moderate size
    "elegant": {
        "font_name": "Liberation Sans",
        "font_size": 68,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00DDDDDD",
        "outline_color": "&H00111111",
        "shadow_color": "&H40000000",
        "bold": 0,
        "outline": 3,
        "shadow": 1,
        "uppercase": False,
        "words_per_group": 4,
        "margin_v": 100,
    },
    # Pixel — retro/gaming style
    "pixel": {
        "font_name": "Liberation Mono",
        "font_size": 72,
        "primary_color": "&H0000FF00",  # lime green
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "shadow_color": "&H00000000",
        "bold": 1,
        "outline": 4,
        "shadow": 1,
        "uppercase": True,
        "words_per_group": 2,
        "margin_v": 110,
    },
    # Clarity — high legibility, no frills
    "clarity": {
        "font_name": "Liberation Sans",
        "font_size": 76,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "bold": 0,
        "outline": 4,
        "shadow": 2,
        "uppercase": False,
        "words_per_group": 5,
        "margin_v": 100,
    },
}

DEFAULT_STYLE = "capcut"
WHISPER_MODEL_SIZE = "small"


def _notify_progress(callback: Callable[[str], None] | None, phase: str) -> None:
    if callback is None:
        return
    try:
        callback(phase)
    except Exception:  # pragma: no cover - progress must never break the render path
        logger.debug("caption_progress_callback_failed phase=%s", phase, exc_info=True)


def _detect_cuda_available() -> bool:
    try:
        import ctranslate2  # type: ignore[import]
    except ImportError:
        return False

    try:
        return int(ctranslate2.get_cuda_device_count()) > 0
    except Exception:
        return False


def _whisper_cache_dir(settings: Settings | None) -> str:
    configured = (
        settings.faster_whisper_cache_dir_resolved
        if settings is not None
        else os.getenv("FASTER_WHISPER_CACHE_DIR") or "/models/faster-whisper"
    )
    path = Path(configured)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _whisper_device_candidates(settings: Settings | None) -> list[str]:
    requested = (
        (settings.faster_whisper_device if settings is not None else os.getenv("FASTER_WHISPER_DEVICE", "auto"))
        or "auto"
    ).lower()
    if requested == "cpu":
        return ["cpu"]
    if requested == "cuda":
        return ["cuda", "cpu"]
    return ["cuda", "cpu"] if _detect_cuda_available() else ["cpu"]


def _whisper_compute_type(settings: Settings | None, device: str) -> str:
    if settings is None:
        return "float16" if device == "cuda" else "int8"
    return (
        settings.faster_whisper_cuda_compute_type
        if device == "cuda"
        else settings.faster_whisper_cpu_compute_type
    )


@lru_cache(maxsize=16)
def _load_whisper_model(
    model_size: str,
    device: str,
    compute_type: str,
    cache_dir: str,
):
    from faster_whisper import WhisperModel  # type: ignore[import]

    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=cache_dir,
    )


def _get_whisper_model(
    *,
    model_size: str,
    settings: Settings | None,
    progress_callback: Callable[[str], None] | None,
):
    cache_dir = _whisper_cache_dir(settings)
    last_error: Exception | None = None
    for device in _whisper_device_candidates(settings):
        compute_type = _whisper_compute_type(settings, device)
        try:
            _notify_progress(progress_callback, f"load_model:{device}")
            model = _load_whisper_model(model_size, device, compute_type, cache_dir)
            logger.info(
                "whisper_model_ready model=%s device=%s compute_type=%s cache_dir=%s",
                model_size,
                device,
                compute_type,
                cache_dir,
            )
            return model
        except Exception as exc:
            last_error = exc
            logger.warning(
                "whisper_model_load_failed model=%s device=%s compute_type=%s error=%s",
                model_size,
                device,
                compute_type,
                exc,
            )
    if last_error is not None:
        raise RuntimeError("Unable to initialize faster-whisper model.") from last_error
    raise RuntimeError("Unable to initialize faster-whisper model.")


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class WordEntry:
    word: str
    start: float  # seconds
    end: float    # seconds


@dataclass
class CaptionGroup:
    text: str
    start: float
    end: float
    words: list[WordEntry]


# ── Transcription ──────────────────────────────────────────────────────────────

def transcribe_audio_bytes(
    audio_bytes: bytes,
    *,
    model_size: str = WHISPER_MODEL_SIZE,
    settings: Settings | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[WordEntry]:
    """Write audio bytes to a temp file and transcribe with faster-whisper.

    Returns word-level timestamps as a list of WordEntry.
    Returns empty list if faster-whisper is not installed or no speech is detected.
    """
    try:
        import faster_whisper  # type: ignore[import]  # noqa: F401
    except ImportError:
        logger.warning(
            "faster_whisper_not_installed — subtitles will fall back to text-split timing. "
            "Install with: pip install faster-whisper"
        )
        return []

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = _get_whisper_model(
            model_size=model_size,
            settings=settings,
            progress_callback=progress_callback,
        )
        _notify_progress(progress_callback, "transcribe_audio")
        segments, _info = model.transcribe(
            tmp_path,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        words: list[WordEntry] = []
        for segment in segments:
            if not segment.words:
                continue
            for w in segment.words:
                word_text = w.word.strip()
                if word_text:
                    words.append(WordEntry(word=word_text, start=w.start, end=w.end))
        return words
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _transcribe_audio_file(
    audio_path: str,
    model_size: str = WHISPER_MODEL_SIZE,
    *,
    settings: Settings | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[WordEntry]:
    try:
        import faster_whisper  # type: ignore[import]  # noqa: F401
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")

    model = _get_whisper_model(
        model_size=model_size,
        settings=settings,
        progress_callback=progress_callback,
    )
    _notify_progress(progress_callback, "transcribe_audio")
    segments, _info = model.transcribe(
        audio_path,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    words: list[WordEntry] = []
    for segment in segments:
        if not segment.words:
            continue
        for w in segment.words:
            word_text = w.word.strip()
            if word_text:
                words.append(WordEntry(word=word_text, start=w.start, end=w.end))
    return words


def _group_words(words: list[WordEntry], words_per_group: int) -> list[CaptionGroup]:
    groups: list[CaptionGroup] = []
    for i in range(0, len(words), words_per_group):
        chunk = words[i : i + words_per_group]
        text = " ".join(w.word for w in chunk)
        groups.append(CaptionGroup(
            text=text,
            start=chunk[0].start,
            end=chunk[-1].end,
            words=chunk,
        ))
    return groups


# ── ASS subtitle generation ────────────────────────────────────────────────────

def _ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def generate_ass(
    words: list[WordEntry],
    *,
    style_name: str = DEFAULT_STYLE,
    video_width: int = 1080,
    video_height: int = 1920,
    words_per_group: int | None = None,
) -> str:
    """Generate an ASS subtitle file string from word-level timestamps.

    Uses \\kf karaoke tags so each word highlights in secondary_color as it's spoken.

    Args:
        words: Word-level timestamps from transcribe_audio_bytes()
        style_name: One of CAPTION_STYLES keys
        video_width / video_height: Target video dimensions
        words_per_group: Override from style (None = use style default)

    Returns:
        ASS file content as a string.
    """
    style = CAPTION_STYLES.get(style_name, CAPTION_STYLES[DEFAULT_STYLE])
    wpg = words_per_group if words_per_group is not None else style["words_per_group"]
    groups = _group_words(words, wpg)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style["font_name"]},{style["font_size"]},{style["primary_color"]},{style["secondary_color"]},{style["outline_color"]},{style["shadow_color"]},{style["bold"]},0,0,0,100,100,0,0,1,{style["outline"]},{style["shadow"]},2,10,10,{style["margin_v"]},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    uppercase = bool(style.get("uppercase"))
    lines: list[str] = []
    for group in groups:
        if group.end <= group.start:
            continue
        if wpg == 1:
            dur_cs = max(1, int((group.end - group.start) * 100))
            word_text = group.text.upper() if uppercase else group.text
            text = f"{{\\kf{dur_cs}}}{word_text}"
        else:
            parts: list[str] = []
            for w in group.words:
                dur_cs = max(1, int((w.end - w.start) * 100))
                wt = w.word.upper() if uppercase else w.word
                parts.append(f"{{\\kf{dur_cs}}}{wt}")
            text = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{_ass_time(group.start)},{_ass_time(group.end)},Default,,0,0,0,,{text}"
        )

    return header + "\n".join(lines) + "\n"


# ── Remix entry point (full pipeline in one call) ──────────────────────────────

def burn_captions(
    settings,
    *,
    video_bytes: bytes,
    style_name: str = DEFAULT_STYLE,
    model_size: str = WHISPER_MODEL_SIZE,
    progress_callback: Callable[[str], None] | None = None,
) -> bytes:
    """Transcribe audio in video_bytes and burn viral captions onto it.

    Args:
        settings: App Settings (provides ffmpeg_bin / ffprobe_bin / ffmpeg_docker_image)
        video_bytes: Raw MP4 bytes (must contain an audio stream)
        style_name: One of CAPTION_STYLES keys
        model_size: Whisper model size (tiny/base/small/medium/large-v3)

    Returns:
        Raw MP4 bytes with captions burned in, or original bytes if transcription fails.
    """
    runner = FFmpegRunner(settings)

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        input_path = workdir / "input.mp4"
        input_path.write_bytes(video_bytes)

        # Extract audio for Whisper
        _notify_progress(progress_callback, "extract_audio")
        runner.run(
            "ffmpeg",
            ["-y", "-i", "input.mp4", "-ar", "16000", "-ac", "1", "-q:a", "0", "-map", "a", "audio.wav"],
            workdir=workdir,
        )

        words = _transcribe_audio_file(
            str(workdir / "audio.wav"),
            model_size=model_size,
            settings=settings,
            progress_callback=progress_callback,
        )
        if not words:
            return video_bytes

        # Probe video dimensions
        _notify_progress(progress_callback, "probe_video")
        probe = runner.probe("input.mp4", workdir=workdir)
        video_stream = next(
            (s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {}
        )
        width = int(video_stream.get("width") or 1080)
        height = int(video_stream.get("height") or 1920)

        # Generate ASS and burn
        _notify_progress(progress_callback, "generate_ass")
        ass_content = generate_ass(words, style_name=style_name, video_width=width, video_height=height)
        (workdir / "captions.ass").write_text(ass_content, encoding="utf-8")

        _notify_progress(progress_callback, "burn_ass")
        runner.run(
            "ffmpeg",
            [
                "-y", "-i", "input.mp4",
                "-vf", "ass=captions.ass",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "output.mp4",
            ],
            workdir=workdir,
        )

        return (workdir / "output.mp4").read_bytes()
