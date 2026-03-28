from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, require_auth
from app.schemas.presets import (
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
