from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.renders import (
    ExportResponse,
    RenderCreateRequest,
    RenderCreateResponse,
    RenderEventResponse,
    RenderJobResponse,
)
from app.services.render_service import RenderService

router = APIRouter()


@router.post(
    "/{project_id}/renders",
    response_model=RenderCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_render(
    project_id: str,
    payload: RenderCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).queue_render_job(
        auth,
        project_id,
        payload,
        idempotency_key=idempotency_key,
    )


@router.get("/{project_id}/exports", response_model=list[ExportResponse])
def list_exports(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).list_exports(auth, project_id)

standalone_router = APIRouter()


@standalone_router.get("/{render_job_id}", response_model=RenderJobResponse)
def get_render_detail(
    render_job_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).get_render_detail(auth, render_job_id)


@standalone_router.post("/{render_job_id}:cancel", response_model=RenderJobResponse)
def cancel_render(
    render_job_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).cancel_render(auth, render_job_id)


@standalone_router.post("/{render_job_id}/steps/{step_id}:retry", response_model=RenderJobResponse)
def retry_render_step(
    render_job_id: str,
    step_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).retry_step(auth, render_job_id, step_id)


@standalone_router.post(
    "/{render_job_id}/steps/{step_id}:approve-frame-pair",
    response_model=RenderJobResponse,
)
def approve_frame_pair(
    render_job_id: str,
    step_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).approve_frame_pair(auth, render_job_id, step_id)


@standalone_router.post(
    "/{render_job_id}/steps/{step_id}:regenerate-frame-pair",
    response_model=RenderJobResponse,
)
def regenerate_frame_pair(
    render_job_id: str,
    step_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).regenerate_frame_pair(auth, render_job_id, step_id)


@standalone_router.get("/{render_job_id}/events", response_model=list[RenderEventResponse])
def get_render_events(
    render_job_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RenderService(db, settings).list_render_events(auth, render_job_id)
