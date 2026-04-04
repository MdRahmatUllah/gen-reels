from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import AuditEvent
from app.models.youtube import AuditLog


def record_audit_event(
    db: Session,
    *,
    workspace_id,
    user_id,
    event_type: str,
    target_type: str,
    target_id: str | None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditEvent(
            workspace_id=workspace_id,
            user_id=user_id,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
        )
    )


def record_structured_audit_log(
    db: Session,
    *,
    workspace_id,
    user_id,
    action: str,
    target_type: str,
    target_id: str | None,
    status: str = "success",
    message: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            status=status,
            message=message,
            payload=payload or {},
        )
    )
