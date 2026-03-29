from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, require_auth
from app.schemas.comments import (
    CommentCreateRequest,
    CommentResolveRequest,
    CommentResponse,
)
from app.services.comment_service import CommentService

router = APIRouter()


@router.get("", response_model=list[CommentResponse])
def list_comments(
    project_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return CommentService(db).list_comments(
        auth,
        project_id=project_id,
        target_type=target_type,
        target_id=target_id,
    )


@router.post("", response_model=CommentResponse)
def create_comment(
    payload: CommentCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return CommentService(db).create_comment(auth, payload)


@router.post("/{comment_id}:resolve", response_model=CommentResponse)
def resolve_comment(
    comment_id: str,
    payload: CommentResolveRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
):
    return CommentService(db).resolve_comment(auth, comment_id, payload)
