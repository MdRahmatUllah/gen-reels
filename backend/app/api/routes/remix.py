from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.remix import (
    RemixAnalyzeResponse,
    RemixJobResponse,
    RemixProjectCreate,
    RemixProjectResponse,
)
from app.services.remix_service import RemixService

router = APIRouter()


@router.get("/projects", response_model=list[RemixProjectResponse])
def list_projects(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).list_projects(auth)


@router.post("/projects", response_model=RemixProjectResponse, status_code=201)
def create_project(
    payload: RemixProjectCreate,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).create_project(auth, payload)


@router.get("/projects/{project_id}", response_model=RemixProjectResponse)
def get_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).get_project(auth, project_id)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    RemixService(db, settings).delete_project(auth, project_id)


@router.get("/projects/{project_id}/analyze", response_model=RemixAnalyzeResponse)
def analyze_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).analyze(auth, project_id)


@router.post("/projects/{project_id}/jobs", response_model=RemixJobResponse, status_code=202)
def create_job(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).create_job(auth, project_id)


@router.get("/projects/{project_id}/jobs", response_model=list[RemixJobResponse])
def list_jobs(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).list_jobs(auth, project_id)


@router.get("/jobs/{job_id}", response_model=RemixJobResponse)
def get_job(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).get_job(auth, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=RemixJobResponse)
def cancel_job(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return RemixService(db, settings).cancel_job(auth, job_id)
