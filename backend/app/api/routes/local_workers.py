from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    LocalWorkerAuthContext,
    ApiKeyAuthContext,
    get_db_dep,
    get_settings_dep,
    get_storage_dep,
    require_local_worker_token,
    require_workspace_api_key,
)
from app.schemas.execution import (
    LocalWorkerHeartbeatRequest,
    LocalWorkerJobPollResponse,
    LocalWorkerJobResultRequest,
    LocalWorkerJobResultResponse,
    LocalWorkerRegisterRequest,
    LocalWorkerRegisterResponse,
    LocalWorkerResponse,
)
from app.services.local_worker_service import LocalWorkerService

router = APIRouter()


@router.post("/register", response_model=LocalWorkerRegisterResponse)
def register_local_worker(
    payload: LocalWorkerRegisterRequest,
    auth: ApiKeyAuthContext = Depends(require_workspace_api_key),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    storage=Depends(get_storage_dep),
):
    return LocalWorkerService(db, settings, storage).register_worker(auth, payload)


@router.post("/{worker_id}/heartbeat", response_model=LocalWorkerResponse)
def local_worker_heartbeat(
    worker_id: str,
    payload: LocalWorkerHeartbeatRequest,
    auth: LocalWorkerAuthContext = Depends(require_local_worker_token),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    storage=Depends(get_storage_dep),
):
    return LocalWorkerService(db, settings, storage).heartbeat(auth, worker_id, payload)


@router.get("/{worker_id}/jobs/next", response_model=LocalWorkerJobPollResponse)
def poll_next_local_worker_job(
    worker_id: str,
    auth: LocalWorkerAuthContext = Depends(require_local_worker_token),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    storage=Depends(get_storage_dep),
):
    return LocalWorkerService(db, settings, storage).poll_next_job(auth, worker_id)


@router.post("/{worker_id}/jobs/{render_step_id}/result", response_model=LocalWorkerJobResultResponse)
def submit_local_worker_job_result(
    worker_id: str,
    render_step_id: str,
    payload: LocalWorkerJobResultRequest,
    auth: LocalWorkerAuthContext = Depends(require_local_worker_token),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
    storage=Depends(get_storage_dep),
):
    return LocalWorkerService(db, settings, storage).submit_job_result(
        auth,
        worker_id,
        render_step_id,
        payload,
    )
