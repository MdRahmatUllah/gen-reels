from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import AuditEvent


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
