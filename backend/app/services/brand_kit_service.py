from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import (
    BrandEnforcementMode,
    BrandKit,
    BrandKitStatus,
    Project,
    VisualPreset,
    VoicePreset,
)
from app.schemas.brand_kits import BrandKitCreateRequest, BrandKitUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.permissions import require_workspace_admin
from app.services.presenters import brand_kit_to_dict
from app.services.project_profiles import (
    merge_profile_overrides,
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)


class BrandKitService:
    def __init__(self, db) -> None:
        self.db = db

    def get_brand_kit(self, workspace_id: str, brand_kit_id: str) -> BrandKit:
        brand_kit = self.db.scalar(
            select(BrandKit).where(
                BrandKit.id == UUID(brand_kit_id),
                BrandKit.workspace_id == UUID(workspace_id),
            )
        )
        if not brand_kit:
            raise ApiError(404, "brand_kit_not_found", "Brand kit not found.")
        return brand_kit

    def get_default_brand_kit(self, workspace_id: str) -> BrandKit | None:
        return self.db.scalar(
            select(BrandKit).where(
                BrandKit.workspace_id == UUID(workspace_id),
                BrandKit.is_default.is_(True),
                BrandKit.status == BrandKitStatus.active,
            )
        )

    def resolve_brand_kit(self, workspace_id: str, brand_kit_id: str | None) -> BrandKit | None:
        if brand_kit_id:
            return self.get_brand_kit(workspace_id, brand_kit_id)
        return self.get_default_brand_kit(workspace_id)

    def _ensure_workspace_preset(self, workspace_id: UUID, preset_model, preset_id: str | None) -> UUID | None:
        if not preset_id:
            return None
        preset = self.db.scalar(
            select(preset_model).where(
                preset_model.id == UUID(str(preset_id)),
                preset_model.workspace_id == workspace_id,
            )
        )
        if not preset:
            raise ApiError(404, "preset_not_found", "Preset not found in this workspace.")
        return preset.id

    def list_brand_kits(self, auth: AuthContext) -> list[dict[str, object]]:
        brand_kits = self.db.scalars(
            select(BrandKit)
            .where(BrandKit.workspace_id == UUID(auth.workspace_id))
            .order_by(BrandKit.updated_at.desc(), BrandKit.created_at.desc())
        ).all()
        return [brand_kit_to_dict(brand_kit) for brand_kit in brand_kits]

    def create_brand_kit(self, auth: AuthContext, payload: BrandKitCreateRequest) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage brand kits.")
        workspace_id = UUID(auth.workspace_id)
        if payload.is_default:
            for existing in self.db.scalars(
                select(BrandKit).where(
                    BrandKit.workspace_id == workspace_id,
                    BrandKit.is_default.is_(True),
                )
            ).all():
                existing.is_default = False

        brand_kit = BrandKit(
            workspace_id=workspace_id,
            created_by_user_id=UUID(auth.user_id),
            default_visual_preset_id=self._ensure_workspace_preset(
                workspace_id,
                VisualPreset,
                payload.default_visual_preset_id,
            ),
            default_voice_preset_id=self._ensure_workspace_preset(
                workspace_id,
                VoicePreset,
                payload.default_voice_preset_id,
            ),
            name=payload.name,
            description=payload.description,
            status=BrandKitStatus(payload.status),
            enforcement_mode=BrandEnforcementMode(payload.enforcement_mode),
            is_default=payload.is_default,
            required_terms=payload.required_terms,
            banned_terms=payload.banned_terms,
            subtitle_style_override=payload.subtitle_style_override,
            export_profile_override=payload.export_profile_override,
            audio_mix_profile_override=payload.audio_mix_profile_override,
            brand_rules=payload.brand_rules,
        )
        self.db.add(brand_kit)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=brand_kit.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="brand_kits.created",
            target_type="brand_kit",
            target_id=str(brand_kit.id),
            payload={"name": brand_kit.name},
        )
        self.db.commit()
        self.db.refresh(brand_kit)
        return brand_kit_to_dict(brand_kit)

    def update_brand_kit(
        self,
        auth: AuthContext,
        brand_kit_id: str,
        payload: BrandKitUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage brand kits.")
        brand_kit = self.get_brand_kit(auth.workspace_id, brand_kit_id)
        if payload.version is not None and brand_kit.version != payload.version:
            raise ApiError(
                409,
                "brand_kit_conflict",
                "This brand kit was changed by another user.",
                details={"current": brand_kit_to_dict(brand_kit)},
            )
        workspace_id = UUID(auth.workspace_id)
        if payload.is_default:
            for existing in self.db.scalars(
                select(BrandKit).where(
                    BrandKit.workspace_id == workspace_id,
                    BrandKit.is_default.is_(True),
                    BrandKit.id != brand_kit.id,
                )
            ).all():
                existing.is_default = False

        for field_name in payload.model_fields_set:
            if field_name == "version":
                continue
            if field_name == "default_visual_preset_id":
                brand_kit.default_visual_preset_id = self._ensure_workspace_preset(
                    workspace_id,
                    VisualPreset,
                    payload.default_visual_preset_id,
                )
            elif field_name == "default_voice_preset_id":
                brand_kit.default_voice_preset_id = self._ensure_workspace_preset(
                    workspace_id,
                    VoicePreset,
                    payload.default_voice_preset_id,
                )
            elif field_name == "status" and payload.status is not None:
                brand_kit.status = BrandKitStatus(payload.status)
            elif field_name == "enforcement_mode" and payload.enforcement_mode is not None:
                brand_kit.enforcement_mode = BrandEnforcementMode(payload.enforcement_mode)
            else:
                setattr(brand_kit, field_name, getattr(payload, field_name))

        brand_kit.version += 1
        record_audit_event(
            self.db,
            workspace_id=brand_kit.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="brand_kits.updated",
            target_type="brand_kit",
            target_id=str(brand_kit.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(brand_kit)
        return brand_kit_to_dict(brand_kit)

    def apply_brand_kit_defaults(self, project: Project, brand_kit: BrandKit | None) -> None:
        if not brand_kit or brand_kit.status == BrandKitStatus.archived:
            return
        project.brand_kit_id = brand_kit.id
        if brand_kit.default_visual_preset_id and (
            brand_kit.enforcement_mode == BrandEnforcementMode.enforced or not project.default_visual_preset_id
        ):
            project.default_visual_preset_id = brand_kit.default_visual_preset_id
        if brand_kit.default_voice_preset_id and (
            brand_kit.enforcement_mode == BrandEnforcementMode.enforced or not project.default_voice_preset_id
        ):
            project.default_voice_preset_id = brand_kit.default_voice_preset_id

        if brand_kit.enforcement_mode == BrandEnforcementMode.enforced:
            project.subtitle_style_profile = normalize_subtitle_style_profile(
                merge_profile_overrides(project.subtitle_style_profile, brand_kit.subtitle_style_override)
            )
            project.export_profile = normalize_export_profile(
                merge_profile_overrides(project.export_profile, brand_kit.export_profile_override)
            )
            project.audio_mix_profile = normalize_audio_mix_profile(
                merge_profile_overrides(project.audio_mix_profile, brand_kit.audio_mix_profile_override)
            )

    def validate_text_against_brand_kit(self, project: Project, text: str) -> None:
        if not project.brand_kit_id:
            return
        brand_kit = self.db.get(BrandKit, project.brand_kit_id)
        if not brand_kit or brand_kit.enforcement_mode != BrandEnforcementMode.enforced:
            return
        lowered = text.lower()
        missing_terms = [
            term for term in (brand_kit.required_terms or []) if term.strip() and term.lower() not in lowered
        ]
        banned_terms = [
            term for term in (brand_kit.banned_terms or []) if term.strip() and term.lower() in lowered
        ]
        if missing_terms or banned_terms:
            raise ApiError(
                400,
                "brand_kit_violation",
                "The content does not satisfy the active brand kit rules.",
                details={"missing_terms": missing_terms, "banned_terms": banned_terms},
            )
