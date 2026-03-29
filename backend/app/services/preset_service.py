from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import VisualPreset, VoicePreset
from app.schemas.presets import (
    VisualPresetCreateRequest,
    VisualPresetUpdateRequest,
    VoicePresetCreateRequest,
    VoicePresetUpdateRequest,
)
from app.services.audit_service import record_audit_event
from app.services.permissions import require_workspace_edit
from app.services.presenters import visual_preset_to_dict, voice_preset_to_dict


class PresetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_visual_preset(self, workspace_id: str, preset_id: str) -> VisualPreset:
        preset = self.db.scalar(
            select(VisualPreset).where(
                VisualPreset.id == UUID(preset_id),
                VisualPreset.workspace_id == UUID(workspace_id),
            )
        )
        if not preset:
            raise ApiError(404, "visual_preset_not_found", "Visual preset not found.")
        return preset

    def get_voice_preset(self, workspace_id: str, preset_id: str) -> VoicePreset:
        preset = self.db.scalar(
            select(VoicePreset).where(
                VoicePreset.id == UUID(preset_id),
                VoicePreset.workspace_id == UUID(workspace_id),
            )
        )
        if not preset:
            raise ApiError(404, "voice_preset_not_found", "Voice preset not found.")
        return preset

    def list_visual_presets(self, auth: AuthContext) -> list[dict[str, object]]:
        presets = self.db.scalars(
            select(VisualPreset)
            .where(VisualPreset.workspace_id == UUID(auth.workspace_id))
            .order_by(VisualPreset.updated_at.desc(), VisualPreset.created_at.desc())
        ).all()
        return [visual_preset_to_dict(preset) for preset in presets]

    def create_visual_preset(
        self,
        auth: AuthContext,
        payload: VisualPresetCreateRequest,
    ) -> dict[str, object]:
        require_workspace_edit(auth, message="Only workspace members or admins can create presets.")
        preset = VisualPreset(
            workspace_id=UUID(auth.workspace_id),
            created_by_user_id=UUID(auth.user_id),
            **payload.model_dump(),
        )
        self.db.add(preset)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=preset.workspace_id,
            user_id=preset.created_by_user_id,
            event_type="presets.visual_created",
            target_type="visual_preset",
            target_id=str(preset.id),
            payload={"name": preset.name},
        )
        self.db.commit()
        self.db.refresh(preset)
        return visual_preset_to_dict(preset)

    def update_visual_preset(
        self,
        auth: AuthContext,
        preset_id: str,
        payload: VisualPresetUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_edit(auth, message="Only workspace members or admins can update presets.")
        preset = self.get_visual_preset(auth.workspace_id, preset_id)
        if payload.version is not None and payload.version != preset.version:
            raise ApiError(
                409,
                "visual_preset_conflict",
                "This visual preset changed since you last loaded it.",
                details={
                    "expected_version": payload.version,
                    "current_version": preset.version,
                    "current": visual_preset_to_dict(preset),
                },
            )
        for field_name in payload.model_fields_set:
            if field_name == "version":
                continue
            setattr(preset, field_name, getattr(payload, field_name))
        preset.version += 1
        record_audit_event(
            self.db,
            workspace_id=preset.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="presets.visual_updated",
            target_type="visual_preset",
            target_id=str(preset.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(preset)
        return visual_preset_to_dict(preset)

    def list_voice_presets(self, auth: AuthContext) -> list[dict[str, object]]:
        presets = self.db.scalars(
            select(VoicePreset)
            .where(VoicePreset.workspace_id == UUID(auth.workspace_id))
            .order_by(VoicePreset.updated_at.desc(), VoicePreset.created_at.desc())
        ).all()
        return [voice_preset_to_dict(preset) for preset in presets]

    def create_voice_preset(
        self,
        auth: AuthContext,
        payload: VoicePresetCreateRequest,
    ) -> dict[str, object]:
        require_workspace_edit(auth, message="Only workspace members or admins can create presets.")
        preset = VoicePreset(
            workspace_id=UUID(auth.workspace_id),
            created_by_user_id=UUID(auth.user_id),
            **payload.model_dump(),
        )
        self.db.add(preset)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=preset.workspace_id,
            user_id=preset.created_by_user_id,
            event_type="presets.voice_created",
            target_type="voice_preset",
            target_id=str(preset.id),
            payload={"name": preset.name},
        )
        self.db.commit()
        self.db.refresh(preset)
        return voice_preset_to_dict(preset)

    def update_voice_preset(
        self,
        auth: AuthContext,
        preset_id: str,
        payload: VoicePresetUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_edit(auth, message="Only workspace members or admins can update presets.")
        preset = self.get_voice_preset(auth.workspace_id, preset_id)
        if payload.version is not None and payload.version != preset.version:
            raise ApiError(
                409,
                "voice_preset_conflict",
                "This voice preset changed since you last loaded it.",
                details={
                    "expected_version": payload.version,
                    "current_version": preset.version,
                    "current": voice_preset_to_dict(preset),
                },
            )
        for field_name in payload.model_fields_set:
            if field_name == "version":
                continue
            setattr(preset, field_name, getattr(payload, field_name))
        preset.version += 1
        record_audit_event(
            self.db,
            workspace_id=preset.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="presets.voice_updated",
            target_type="voice_preset",
            target_id=str(preset.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(preset)
        return voice_preset_to_dict(preset)
