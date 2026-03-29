from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.common import JobAcceptedResponse
from app.schemas.projects import ScriptVersionResponse
from app.schemas.scripts import ScriptPatchRequest
from app.services.content_planning_service import ContentPlanningService
from app.services.generation_service import GenerationService
from app.services.routing_service import RoutingService

router = APIRouter()


@router.get("/{project_id}/scripts", response_model=list[ScriptVersionResponse])
def list_scripts(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return GenerationService(db, settings).list_scripts(auth, project_id)


@router.post(
    "/{project_id}/scripts:generate",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_script(
    project_id: str,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider, _decision = RoutingService(db, settings).build_moderation_provider_for_workspace(
        auth.workspace_id
    )
    return GenerationService(db, settings).queue_script_generation(
        auth,
        project_id,
        idempotency_key=idempotency_key,
        moderation_provider=moderation_provider,
    )


@router.patch("/{project_id}/scripts/{script_version_id}", response_model=ScriptVersionResponse)
def patch_script(
    project_id: str,
    script_version_id: str,
    payload: ScriptPatchRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return GenerationService(db, settings).patch_script(auth, project_id, script_version_id, payload)


@router.post("/{project_id}/scripts/{script_version_id}:approve", response_model=ScriptVersionResponse)
def approve_script(
    project_id: str,
    script_version_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ContentPlanningService(db, settings).approve_script(auth, project_id, script_version_id)
