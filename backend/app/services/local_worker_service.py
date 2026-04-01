from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.api.deps import ApiKeyAuthContext, AuthContext, LocalWorkerAuthContext
from app.core.errors import ApiError
from app.core.security import generate_token, hash_token
from app.integrations.storage import StorageClient
from app.models.entities import (
    ExecutionMode,
    LocalWorker,
    LocalWorkerHeartbeat,
    LocalWorkerStatus,
    ProviderRun,
    ProviderRunStatus,
    WorkspaceRole,
)
from app.schemas.execution import (
    LocalWorkerHeartbeatRequest,
    LocalWorkerJobPollResponse,
    LocalWorkerJobResultRequest,
    LocalWorkerRegisterRequest,
)
from app.services.audit_service import record_audit_event
from app.services.permissions import require_workspace_admin
from app.services.render_service import RenderService
from app.services.routing_service import RoutingService


class LocalWorkerService:
    def __init__(self, db, settings, storage: StorageClient) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage

    @staticmethod
    def _to_dict(worker: LocalWorker) -> dict[str, object]:
        return {
            "id": worker.id,
            "workspace_id": worker.workspace_id,
            "registered_by_api_key_id": worker.registered_by_api_key_id,
            "name": worker.name,
            "status": worker.status.value,
            "token_prefix": worker.token_prefix,
            "supports_ordered_reference_images": worker.supports_ordered_reference_images,
            "supports_first_last_frame_video": worker.supports_first_last_frame_video,
            "supports_tts": worker.supports_tts,
            "supports_clip_retime": worker.supports_clip_retime,
            "metadata_payload": worker.metadata_payload,
            "last_heartbeat_at": worker.last_heartbeat_at,
            "last_polled_at": worker.last_polled_at,
            "last_job_claimed_at": worker.last_job_claimed_at,
            "last_error_at": worker.last_error_at,
            "last_error_code": worker.last_error_code,
            "last_error_message": worker.last_error_message,
            "revoked_at": worker.revoked_at,
            "created_at": worker.created_at,
            "updated_at": worker.updated_at,
        }

    def _worker(self, workspace_id: str | UUID, worker_id: str | UUID) -> LocalWorker:
        worker = self.db.scalar(
            select(LocalWorker).where(
                LocalWorker.id == UUID(str(worker_id)),
                LocalWorker.workspace_id == UUID(str(workspace_id)),
            )
        )
        if not worker:
            raise ApiError(404, "local_worker_not_found", "Local worker not found.")
        return worker

    def list_workers(self, auth: AuthContext) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can manage local workers.")
        RoutingService(self.db, self.settings).refresh_worker_statuses()
        workers = self.db.scalars(
            select(LocalWorker)
            .where(LocalWorker.workspace_id == UUID(auth.workspace_id))
            .order_by(LocalWorker.created_at.desc())
        ).all()
        return [self._to_dict(worker) for worker in workers]

    def revoke_worker(self, auth: AuthContext, worker_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage local workers.")
        worker = self._worker(auth.workspace_id, worker_id)
        worker.status = LocalWorkerStatus.revoked
        worker.revoked_at = worker.revoked_at or datetime.now(timezone.utc)
        record_audit_event(
            self.db,
            workspace_id=worker.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.local_worker_revoked",
            target_type="local_worker",
            target_id=str(worker.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(worker)
        return self._to_dict(worker)

    def register_worker(
        self,
        auth: ApiKeyAuthContext,
        payload: LocalWorkerRegisterRequest,
    ) -> dict[str, object]:
        if auth.role_scope not in {WorkspaceRole.admin, WorkspaceRole.member}:
            raise ApiError(
                403,
                "forbidden",
                "That API key does not have permission to register local workers.",
            )
        raw_worker_token = f"rglw_{generate_token(32)}"
        now = datetime.now(timezone.utc)
        worker = LocalWorker(
            workspace_id=UUID(auth.workspace_id),
            registered_by_api_key_id=UUID(auth.api_key_id),
            name=payload.name,
            status=LocalWorkerStatus.online,
            worker_token_hash=hash_token(raw_worker_token),
            token_prefix=raw_worker_token[:12],
            supports_ordered_reference_images=payload.supports_ordered_reference_images,
            supports_first_last_frame_video=payload.supports_first_last_frame_video,
            supports_tts=payload.supports_tts,
            supports_clip_retime=payload.supports_clip_retime,
            metadata_payload=payload.metadata_payload,
            last_heartbeat_at=now,
        )
        self.db.add(worker)
        self.db.flush()
        self.db.add(
            LocalWorkerHeartbeat(
                worker_id=worker.id,
                workspace_id=worker.workspace_id,
                status=worker.status,
                metadata_payload=payload.metadata_payload,
            )
        )
        record_audit_event(
            self.db,
            workspace_id=worker.workspace_id,
            user_id=None,
            event_type="workspace.local_worker_registered",
            target_type="local_worker",
            target_id=str(worker.id),
            payload={"name": worker.name},
        )
        self.db.commit()
        self.db.refresh(worker)
        return {**self._to_dict(worker), "worker_token": raw_worker_token}

    def heartbeat(
        self,
        auth: LocalWorkerAuthContext,
        worker_id: str,
        payload: LocalWorkerHeartbeatRequest,
    ) -> dict[str, object]:
        if auth.worker_id != worker_id:
            raise ApiError(403, "forbidden", "Worker token does not match the requested worker.")
        worker = self._worker(auth.workspace_id, worker_id)
        worker.status = LocalWorkerStatus.online
        worker.last_heartbeat_at = datetime.now(timezone.utc)
        worker.metadata_payload = {
            **dict(worker.metadata_payload or {}),
            **dict(payload.metadata_payload or {}),
        }
        self.db.add(
            LocalWorkerHeartbeat(
                worker_id=worker.id,
                workspace_id=worker.workspace_id,
                status=worker.status,
                metadata_payload=payload.metadata_payload,
            )
        )
        self.db.commit()
        self.db.refresh(worker)
        return self._to_dict(worker)

    def poll_next_job(
        self,
        auth: LocalWorkerAuthContext,
        worker_id: str,
    ) -> dict[str, object]:
        if auth.worker_id != worker_id:
            raise ApiError(403, "forbidden", "Worker token does not match the requested worker.")
        worker = self._worker(auth.workspace_id, worker_id)
        if worker.status == LocalWorkerStatus.revoked or worker.revoked_at is not None:
            raise ApiError(403, "worker_revoked", "This local worker has been revoked.")
        worker.status = LocalWorkerStatus.online
        worker.last_polled_at = datetime.now(timezone.utc)
        provider_run = self.db.scalar(
            select(ProviderRun)
            .where(
                ProviderRun.worker_id == worker.id,
                ProviderRun.execution_mode == ExecutionMode.local,
                ProviderRun.status == ProviderRunStatus.queued,
            )
            .order_by(ProviderRun.started_at.asc())
        )
        if not provider_run:
            self.db.commit()
            return LocalWorkerJobPollResponse(job=None).model_dump()

        provider_run.status = ProviderRunStatus.running
        worker.last_job_claimed_at = datetime.now(timezone.utc)
        self.db.commit()
        payload = dict(provider_run.request_payload or {})
        job = {
            "provider_run_id": provider_run.id,
            "render_job_id": provider_run.render_job_id,
            "render_step_id": provider_run.render_step_id,
            **payload,
        }
        return LocalWorkerJobPollResponse(job=job).model_dump()

    def submit_job_result(
        self,
        auth: LocalWorkerAuthContext,
        worker_id: str,
        render_step_id: str,
        payload: LocalWorkerJobResultRequest,
    ) -> dict[str, object]:
        if auth.worker_id != worker_id:
            raise ApiError(403, "forbidden", "Worker token does not match the requested worker.")
        worker = self._worker(auth.workspace_id, worker_id)
        provider_run = self.db.scalar(
            select(ProviderRun)
            .where(
                ProviderRun.worker_id == worker.id,
                ProviderRun.render_step_id == UUID(str(render_step_id)),
                ProviderRun.execution_mode == ExecutionMode.local,
                ProviderRun.status.in_([ProviderRunStatus.queued, ProviderRunStatus.running]),
            )
            .order_by(ProviderRun.started_at.desc())
        )
        if not provider_run:
            raise ApiError(404, "local_worker_job_not_found", "Local worker job not found.")
        result = RenderService(self.db, self.settings, self.storage).handle_local_worker_result(
            worker,
            provider_run,
            payload,
        )
        return result
