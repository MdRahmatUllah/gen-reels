from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, require_auth
from app.schemas.presets import (
    MusicPresetCreateRequest,
    MusicPresetResponse,
    MusicPresetUpdateRequest,
    SubtitlePresetCreateRequest,
    SubtitlePresetResponse,
    SubtitlePresetUpdateRequest,
    VisualPresetCreateRequest,
    VisualPresetResponse,
    VisualPresetUpdateRequest,
    VoicePresetCreateRequest,
    VoicePresetResponse,
    VoicePresetUpdateRequest,
)
from app.services.preset_service import PresetService

router = APIRouter()


@router.get("/visual", response_model=list[VisualPresetResponse])
def list_visual_presets(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).list_visual_presets(auth)


@router.post("/visual", response_model=VisualPresetResponse)
def create_visual_preset(
    payload: VisualPresetCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).create_visual_preset(auth, payload)


@router.patch("/visual/{preset_id}", response_model=VisualPresetResponse)
def patch_visual_preset(
    preset_id: str,
    payload: VisualPresetUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).update_visual_preset(auth, preset_id, payload)


@router.get("/voice", response_model=list[VoicePresetResponse])
def list_voice_presets(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).list_voice_presets(auth)


@router.post("/voice", response_model=VoicePresetResponse)
def create_voice_preset(
    payload: VoicePresetCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).create_voice_preset(auth, payload)


@router.patch("/voice/{preset_id}", response_model=VoicePresetResponse)
def patch_voice_preset(
    preset_id: str,
    payload: VoicePresetUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).update_voice_preset(auth, preset_id, payload)


@router.get("/music", response_model=list[MusicPresetResponse])
def list_music_presets(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).list_music_presets(auth)


@router.post("/music", response_model=MusicPresetResponse)
def create_music_preset(
    payload: MusicPresetCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).create_music_preset(auth, payload)


@router.patch("/music/{preset_id}", response_model=MusicPresetResponse)
def patch_music_preset(
    preset_id: str,
    payload: MusicPresetUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).update_music_preset(auth, preset_id, payload)


@router.get("/subtitle", response_model=list[SubtitlePresetResponse])
def list_subtitle_presets(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).list_subtitle_presets(auth)


@router.post("/subtitle", response_model=SubtitlePresetResponse)
def create_subtitle_preset(
    payload: SubtitlePresetCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).create_subtitle_preset(auth, payload)


@router.patch("/subtitle/{preset_id}", response_model=SubtitlePresetResponse)
def patch_subtitle_preset(
    preset_id: str,
    payload: SubtitlePresetUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return PresetService(db).update_subtitle_preset(auth, preset_id, payload)


BUILT_IN_RENDER_PRESETS = [
    {
        "id": "rp_social_reel",
        "name": "Social Reel",
        "description": "Optimized for Instagram Reels & TikTok with bold captions and upbeat energy",
        "category": "social",
        "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "icon": "social",
        "settings": {
            "animationEffect": "ken_burns",
            "subtitleStyle": "Karaoke Bold",
            "musicTrack": "Upbeat Electronic",
            "musicDucking": "-12 dB",
            "transitionMode": "crossfade",
            "videoEffects": {
                "brightness": 0, "contrast": 8, "saturation": 15,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "none", "vignetteStrength": 20,
            },
        },
        "tags": ["instagram", "tiktok", "vertical", "captions"],
        "recommended": True,
    },
    {
        "id": "rp_corporate",
        "name": "Corporate Clean",
        "description": "Professional and polished look with subtle motion and ambient audio",
        "category": "corporate",
        "gradient": "linear-gradient(135deg, #2c3e50 0%, #3498db 100%)",
        "icon": "corporate",
        "settings": {
            "animationEffect": "zoom_in",
            "subtitleStyle": "Minimalist White",
            "musicTrack": "Ambient Corporate 1",
            "musicDucking": "-18 dB",
            "transitionMode": "crossfade",
            "videoEffects": {
                "brightness": 0, "contrast": 5, "saturation": 0,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "none", "vignetteStrength": 0,
            },
        },
        "tags": ["professional", "business", "clean"],
    },
    {
        "id": "rp_cinematic",
        "name": "Cinematic Story",
        "description": "Moody color grading with slow pans and dramatic feel",
        "category": "cinematic",
        "gradient": "linear-gradient(135deg, #0c0c1d 0%, #3a1c71 50%, #d76d77 100%)",
        "icon": "cinematic",
        "settings": {
            "animationEffect": "pan_left",
            "subtitleStyle": "none",
            "musicTrack": "Lo-fi Chill",
            "musicDucking": "-6 dB",
            "transitionMode": "crossfade",
            "videoEffects": {
                "brightness": 0, "contrast": 12, "saturation": -10,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "moody", "vignetteStrength": 40,
            },
        },
        "tags": ["film", "dramatic", "storytelling"],
    },
    {
        "id": "rp_quick_share",
        "name": "Quick Share",
        "description": "Minimal processing for fast renders — no subtitles, no music",
        "category": "minimal",
        "gradient": "linear-gradient(135deg, #e0e0e0 0%, #bdbdbd 100%)",
        "icon": "minimal",
        "settings": {
            "animationEffect": "ken_burns",
            "subtitleStyle": "none",
            "musicTrack": "none",
            "musicDucking": "0 dB",
            "transitionMode": "hard_cut",
            "videoEffects": {
                "brightness": 0, "contrast": 0, "saturation": 0,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "none", "vignetteStrength": 0,
            },
        },
        "tags": ["fast", "simple", "no-frills"],
    },
    {
        "id": "rp_podcast_clip",
        "name": "Podcast Clip",
        "description": "Large readable subtitles with static frames",
        "category": "social",
        "gradient": "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)",
        "icon": "podcast",
        "settings": {
            "animationEffect": "zoom_out",
            "subtitleStyle": "Burned-in Default",
            "musicTrack": "none",
            "musicDucking": "0 dB",
            "transitionMode": "hard_cut",
            "videoEffects": {
                "brightness": 5, "contrast": 0, "saturation": 0,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "none", "vignetteStrength": 0,
            },
        },
        "tags": ["podcast", "subtitles", "accessibility"],
    },
    {
        "id": "rp_product",
        "name": "Product Showcase",
        "description": "Vibrant colors with smooth zoom to highlight product details",
        "category": "corporate",
        "gradient": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "icon": "product",
        "settings": {
            "animationEffect": "zoom_in",
            "subtitleStyle": "Minimalist White",
            "musicTrack": "Ambient Corporate 1",
            "musicDucking": "-12 dB",
            "transitionMode": "crossfade",
            "videoEffects": {
                "brightness": 5, "contrast": 5, "saturation": 20,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "vibrant", "vignetteStrength": 0,
            },
        },
        "tags": ["ecommerce", "product", "vibrant"],
    },
    {
        "id": "rp_vintage",
        "name": "Vintage Nostalgia",
        "description": "Warm sepia tones with film grain feel and gentle motion",
        "category": "cinematic",
        "gradient": "linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)",
        "icon": "vintage",
        "settings": {
            "animationEffect": "pan_right",
            "subtitleStyle": "none",
            "musicTrack": "Lo-fi Chill",
            "musicDucking": "-12 dB",
            "transitionMode": "crossfade",
            "videoEffects": {
                "brightness": 5, "contrast": 8, "saturation": -20,
                "speed": 1.0, "fadeInSec": 0, "fadeOutSec": 0,
                "colorFilter": "vintage", "vignetteStrength": 50,
            },
        },
        "tags": ["retro", "warm", "nostalgic"],
    },
]


@router.get("/render-presets")
def list_render_presets(
    _auth: AuthContext = Depends(require_auth),
):
    return BUILT_IN_RENDER_PRESETS
