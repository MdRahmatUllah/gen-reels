from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import or_, select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.integrations.storage import StorageClient, build_storage_client
from app.models.entities import Asset, AssetRole, AssetType, Project, ScenePlan, SceneSegment
from app.schemas.assets import AssetReuseRequest
from app.services.generation_service import GenerationService
from app.services.presenters import asset_to_dict


class AssetService(GenerationService):
    def __init__(self, db, settings, storage: StorageClient | None = None) -> None:
        super().__init__(db, settings)
        self.storage = storage or build_storage_client(settings)

    def _next_object_name(self, object_name: str) -> str:
        existing = self.db.scalar(select(Asset.id).where(Asset.object_name == object_name))
        if not existing:
            return object_name

        stem, separator, extension = object_name.rpartition(".")
        if not separator:
            stem = object_name
        version = 2
        while True:
            candidate = f"{stem}-v{version}{separator}{extension}" if separator else f"{stem}-v{version}"
            if not self.db.scalar(select(Asset.id).where(Asset.object_name == candidate)):
                return candidate
            version += 1

    def list_library_assets(
        self,
        auth: AuthContext,
        *,
        search: str | None = None,
        asset_role: str | None = None,
        asset_type: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, object]]:
        query = select(Asset).where(
            Asset.workspace_id == UUID(auth.workspace_id),
            Asset.status != "quarantined",
            or_(Asset.is_library_asset.is_(True), Asset.is_reusable.is_(True), Asset.reused_from_asset_id.is_not(None)),
        )
        if asset_role:
            query = query.where(Asset.asset_role == AssetRole(asset_role))
        if asset_type:
            query = query.where(Asset.asset_type == AssetType(asset_type))
        if project_id:
            query = query.where(Asset.project_id == UUID(project_id))

        assets = self.db.scalars(query.order_by(Asset.updated_at.desc(), Asset.created_at.desc())).all()
        if search:
            lowered = search.strip().lower()
            assets = [
                asset
                for asset in assets
                if lowered in (asset.file_name or "").lower()
                or lowered in (asset.library_label or "").lower()
            ]
        return [
            asset_to_dict(asset, download_url=self.storage.presigned_get_url(asset.bucket_name, asset.object_name))
            for asset in assets
        ]

    def reuse_asset(
        self,
        auth: AuthContext,
        asset_id: str,
        payload: AssetReuseRequest,
    ) -> dict[str, object]:
        source_asset = self.db.get(Asset, UUID(asset_id))
        if not source_asset or str(source_asset.workspace_id) != auth.workspace_id:
            raise ApiError(404, "asset_not_found", "Asset not found.")
        if not source_asset.is_reusable and not source_asset.is_library_asset:
            raise ApiError(400, "asset_not_reusable", "This asset is not available for reuse.")

        project = self._get_project(payload.project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        attach_as = payload.attach_as
        target_segment = None
        if payload.target_scene_plan_id or payload.target_scene_index is not None:
            if not payload.target_scene_plan_id or payload.target_scene_index is None:
                raise ApiError(
                    400,
                    "invalid_reuse_target",
                    "Both target_scene_plan_id and target_scene_index are required for scene attachment.",
                )
            scene_plan = self.db.scalar(
                select(ScenePlan).where(
                    ScenePlan.id == UUID(payload.target_scene_plan_id),
                    ScenePlan.project_id == project.id,
                )
            )
            if not scene_plan:
                raise ApiError(404, "scene_plan_not_found", "Scene plan not found.")
            if scene_plan.approval_state == "approved":
                raise ApiError(
                    409,
                    "scene_plan_locked",
                    "Attach reused assets to a draft scene plan, not an approved version.",
                )
            target_segment = self.db.scalar(
                select(SceneSegment).where(
                    SceneSegment.scene_plan_id == scene_plan.id,
                    SceneSegment.scene_index == payload.target_scene_index,
                )
            )
            if not target_segment:
                raise ApiError(404, "scene_segment_not_found", "Scene segment not found.")

        target_bucket = source_asset.bucket_name
        target_object = self._next_object_name(
            (
                f"workspace/{project.workspace_id}/project/{project.id}/"
                f"assets/reuse/{uuid4()}-{source_asset.file_name}"
            )
        )
        self.storage.copy_object(
            source_asset.bucket_name,
            source_asset.object_name,
            target_bucket,
            target_object,
        )

        target_asset_type = source_asset.asset_type
        target_asset_role = source_asset.asset_role
        if attach_as == "continuity_anchor":
            target_asset_type = AssetType.reference_image
            target_asset_role = AssetRole.continuity_anchor
        elif attach_as == "start_frame":
            target_asset_type = AssetType.image
            target_asset_role = AssetRole.scene_start_frame
        elif attach_as == "end_frame":
            target_asset_type = AssetType.image
            target_asset_role = AssetRole.scene_end_frame

        reused_asset = Asset(
            workspace_id=project.workspace_id,
            project_id=project.id,
            scene_segment_id=target_segment.id if target_segment else None,
            asset_type=target_asset_type,
            asset_role=target_asset_role,
            status="completed",
            bucket_name=target_bucket,
            object_name=target_object,
            file_name=source_asset.file_name,
            content_type=source_asset.content_type,
            size_bytes=source_asset.size_bytes,
            duration_ms=source_asset.duration_ms,
            width=source_asset.width,
            height=source_asset.height,
            frame_rate=source_asset.frame_rate,
            library_label=payload.library_label or source_asset.library_label or source_asset.file_name,
            is_library_asset=False,
            is_reusable=False,
            reused_from_asset_id=source_asset.id,
            continuity_score=source_asset.continuity_score,
            reuse_count=0,
            has_audio_stream=source_asset.has_audio_stream,
            source_audio_policy=source_asset.source_audio_policy,
            timing_alignment_strategy=source_asset.timing_alignment_strategy,
            metadata_payload={
                **dict(source_asset.metadata_payload or {}),
                "reused_from_asset_id": str(source_asset.id),
                "reuse_mode": attach_as,
            },
        )
        self.db.add(reused_asset)
        self.db.flush()

        source_asset.reuse_count += 1
        if target_segment:
            if attach_as == "continuity_anchor":
                target_segment.chained_from_asset_id = reused_asset.id
            elif attach_as == "start_frame":
                target_segment.start_image_asset_id = reused_asset.id
            elif attach_as == "end_frame":
                target_segment.end_image_asset_id = reused_asset.id

        self.db.commit()
        self.db.refresh(reused_asset)
        return asset_to_dict(
            reused_asset,
            download_url=self.storage.presigned_get_url(reused_asset.bucket_name, reused_asset.object_name),
        )
