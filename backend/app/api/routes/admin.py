from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.admin import (
    AdminModerationItemResponse,
    AdminModerationReportResponse,
    AdminRenderSummaryResponse,
    ModerationReviewRequest,
)
from app.services.admin_service import AdminService

router = APIRouter()


@router.get("/moderation", response_model=list[AdminModerationItemResponse])
def list_moderation_queue(
    review_status: str | None = Query(default="pending"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).list_moderation(auth, review_status=review_status)


@router.post("/moderation/{moderation_event_id}:release", response_model=AdminModerationItemResponse)
def release_moderation_event(
    moderation_event_id: str,
    payload: ModerationReviewRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).release_moderation(auth, moderation_event_id, notes=payload.notes)


@router.post("/moderation/{moderation_event_id}:reject", response_model=AdminModerationItemResponse)
def reject_moderation_event(
    moderation_event_id: str,
    payload: ModerationReviewRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).reject_moderation(auth, moderation_event_id, notes=payload.notes)


@router.get("/renders", response_model=list[AdminRenderSummaryResponse])
def list_admin_renders(
    status: str | None = None,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).list_renders(auth, status=status)


@router.get("/moderation-reports", response_model=list[AdminModerationReportResponse])
def list_moderation_reports(
    status: str | None = Query(default="pending"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).list_moderation_reports(auth, status=status)


@router.post(
    "/moderation-reports/{report_id}:release",
    response_model=AdminModerationReportResponse,
)
def release_moderation_report(
    report_id: str,
    payload: ModerationReviewRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).release_moderation_report(auth, report_id, notes=payload.notes)


@router.post(
    "/moderation-reports/{report_id}:reject",
    response_model=AdminModerationReportResponse,
)
def reject_moderation_report(
    report_id: str,
    payload: ModerationReviewRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return AdminService(db, settings).reject_moderation_report(auth, report_id, notes=payload.notes)
