from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.reviews import (
    ReviewCreateRequest,
    ReviewDecisionRequest,
    ReviewResponse,
)
from app.services.review_service import ReviewService

router = APIRouter()


@router.get("", response_model=list[ReviewResponse])
def list_reviews(
    project_id: str | None = None,
    status: str | None = None,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ReviewService(db, settings).list_reviews(auth, project_id=project_id, status=status)


@router.post("", response_model=ReviewResponse)
def create_review(
    payload: ReviewCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ReviewService(db, settings).create_review(auth, payload)


@router.post("/{review_id}:approve", response_model=ReviewResponse)
def approve_review(
    review_id: str,
    payload: ReviewDecisionRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ReviewService(db, settings).approve_review(
        auth,
        review_id,
        decision_notes=payload.decision_notes,
    )


@router.post("/{review_id}:reject", response_model=ReviewResponse)
def reject_review(
    review_id: str,
    payload: ReviewDecisionRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return ReviewService(db, settings).reject_review(
        auth,
        review_id,
        decision_notes=payload.decision_notes,
    )
