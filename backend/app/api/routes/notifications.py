from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_db_dep, get_settings_dep, require_auth
from app.schemas.notifications import (
    NotificationEventResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=list[NotificationEventResponse])
def list_notifications(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return NotificationService(db, settings).list_notifications(auth)


@router.post("/{notification_id}:read", response_model=NotificationEventResponse)
def mark_notification_read(
    notification_id: str,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return NotificationService(db, settings).mark_read(auth, notification_id)


@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return NotificationService(db, settings).get_preferences(auth)


@router.put("/preferences", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    payload: NotificationPreferenceUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_dep),
    settings=Depends(get_settings_dep),
):
    return NotificationService(db, settings).update_preferences(auth, payload)

