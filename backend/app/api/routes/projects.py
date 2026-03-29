from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.integrations.azure import build_moderation_provider
from app.schemas.common import MessageResponse
from app.schemas.projects import (
    BriefVersionResponse,
    BriefWriteRequest,
    ProjectLineageResponse,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectService

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ProjectService(db).list_projects(auth)


@router.post("", response_model=ProjectResponse)
def create_project(
    payload: ProjectCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ProjectService(db).create_project(auth, payload)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ProjectService(db).get_project_detail(auth, project_id)


@router.get("/{project_id}/lineage", response_model=ProjectLineageResponse)
def get_project_lineage(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ProjectService(db).get_project_lineage(auth, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return ProjectService(db).update_project(auth, project_id, payload)


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    ProjectService(db).delete_project(auth, project_id)
    return {"message": "Project deleted."}


@router.post("/{project_id}/brief", response_model=BriefVersionResponse)
def create_brief_version(
    project_id: str,
    payload: BriefWriteRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider = build_moderation_provider(settings)
    return ProjectService(db).save_brief_version(auth, project_id, payload, moderation_provider)


@router.patch("/{project_id}/brief", response_model=BriefVersionResponse)
def patch_brief_version(
    project_id: str,
    payload: BriefWriteRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider = build_moderation_provider(settings)
    return ProjectService(db).save_brief_version(auth, project_id, payload, moderation_provider)
