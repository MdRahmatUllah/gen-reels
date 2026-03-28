from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.integrations.azure import build_moderation_provider
from app.schemas.common import JobAcceptedResponse, MessageResponse
from app.schemas.projects import IdeaSetResponse
from app.services.generation_service import GenerationService

router = APIRouter()


@router.get("/{project_id}/ideas", response_model=list[IdeaSetResponse])
def list_ideas(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return GenerationService(db, settings).list_ideas(auth, project_id)


@router.post(
    "/{project_id}/ideas:generate",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_ideas(
    project_id: str,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    moderation_provider = build_moderation_provider(settings)
    return GenerationService(db, settings).queue_idea_generation(
        auth,
        project_id,
        idempotency_key=idempotency_key,
        moderation_provider=moderation_provider,
    )


@router.post("/{project_id}/ideas/{idea_id}:select", response_model=MessageResponse)
def select_idea(
    project_id: str,
    idea_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    result = GenerationService(db, settings).select_idea(auth, project_id, idea_id)
    return {"message": f"Idea {result['idea_id']} selected."}
