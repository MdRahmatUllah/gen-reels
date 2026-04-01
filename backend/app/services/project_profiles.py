from __future__ import annotations

from copy import deepcopy
from typing import Any

_DEFAULT_SUBTITLE_STYLE_PROFILE: dict[str, Any] = {
    "preset": "clean_bold",
    "burn_in": False,
    "font_family": "Montserrat SemiBold",
    "font_size": 56,
    "max_width_pct": 82,
    "alignment": "center",
    "placement": {
        "x_pct": 50,
        "y_pct": 82,
    },
    "text_color": "#FFFFFF",
    "stroke_color": "#101010",
    "stroke_width": 3,
    "shadow_strength": 0.45,
}

_DEFAULT_EXPORT_PROFILE: dict[str, Any] = {
    "format": "mp4",
    "container": "mp4",
    "video_codec": "h264",
    "audio_codec": "aac",
    "resolution": {
        "width": 1080,
        "height": 1920,
    },
    "frame_rate": 24,
    "video_bitrate_kbps": 8000,
    "caption_burn_in": False,
}

_DEFAULT_AUDIO_MIX_PROFILE: dict[str, Any] = {
    "music_enabled": False,
    "music_source": "generated_or_curated",
    "music_gain_db": -20.0,
    "ducking_gain_db": -12.0,
    "ducking_fade_seconds": 0.3,
    "music_fade_out_seconds": 1.5,
    "target_lufs": -14.0,
    "true_peak_dbtp": -1.0,
    "crossfade_enabled": True,
    "crossfade_duration_seconds": 0.2,
}


_DEFAULT_VIDEO_EFFECTS_PROFILE: dict[str, Any] = {
    "brightness": 0.0,
    "contrast": 0.0,
    "saturation": 0.0,
    "speed": 1.0,
    "fade_in_sec": 0.0,
    "fade_out_sec": 0.0,
    "color_filter": "none",
    "vignette_strength": 0.0,
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
            continue
        merged[key] = value
    return merged


def default_subtitle_style_profile() -> dict[str, Any]:
    return deepcopy(_DEFAULT_SUBTITLE_STYLE_PROFILE)


def default_export_profile() -> dict[str, Any]:
    return deepcopy(_DEFAULT_EXPORT_PROFILE)


def default_audio_mix_profile() -> dict[str, Any]:
    return deepcopy(_DEFAULT_AUDIO_MIX_PROFILE)


def merge_profile_overrides(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    return _deep_merge(base or {}, override or {})


def normalize_subtitle_style_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    return _deep_merge(_DEFAULT_SUBTITLE_STYLE_PROFILE, profile or {})


def normalize_export_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    return _deep_merge(_DEFAULT_EXPORT_PROFILE, profile or {})


def normalize_audio_mix_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    return _deep_merge(_DEFAULT_AUDIO_MIX_PROFILE, profile or {})


def default_video_effects_profile() -> dict[str, Any]:
    return deepcopy(_DEFAULT_VIDEO_EFFECTS_PROFILE)


def normalize_video_effects_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    return _deep_merge(_DEFAULT_VIDEO_EFFECTS_PROFILE, profile or {})
