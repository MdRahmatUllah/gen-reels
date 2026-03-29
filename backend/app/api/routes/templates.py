from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, require_auth
from app.schemas.templates import (
    ProjectFromTemplateRequest,
    TemplateCreateRequest,
    TemplateDetailResponse,
    TemplateProjectCreateResponse,
    TemplateResponse,
)
from app.services.project_service import ProjectService
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return TemplateService(db).list_templates(auth)


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(
    template_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return TemplateService(db).get_template_detail(auth, template_id)


@router.post("/{template_id}:create-project", response_model=TemplateProjectCreateResponse)
def create_project_from_template(
    template_id: str,
    payload: ProjectFromTemplateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return TemplateService(db).create_project_from_template(auth, template_id, payload)


@router.post("/from-project/{project_id}", response_model=TemplateResponse)
def create_template_from_project(
    project_id: str,
    payload: TemplateCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    project_service = ProjectService(db)
    project = project_service._get_project(project_id, auth.workspace_id)
    project_service._assert_mutation_rights(project, auth)
    return TemplateService(db).create_template_from_project(auth, project, payload)
