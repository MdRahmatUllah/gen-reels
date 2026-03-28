from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.integrations.azure import ModerationProvider
from app.models.entities import ModerationDecision, ModerationEvent


def moderate_text_or_raise(
    db: Session,
    *,
    provider: ModerationProvider,
    text: str,
    target_type: str,
    user_id,
    project_id=None,
    workspace_id=None,
    target_id: str | None = None,
) -> ModerationEvent:
    result = provider.moderate_text(text, target_type=target_type)
    event = ModerationEvent(
        project_id=project_id,
        workspace_id=workspace_id,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        input_text=text,
        decision=ModerationDecision.blocked if result.blocked else ModerationDecision.allowed,
        provider_name=result.provider_name,
        severity_summary=result.severity_summary,
        response_payload=result.raw_response,
        blocked_message=result.blocked_message,
    )
    db.add(event)
    db.flush()
    if result.blocked:
        db.commit()
        raise ApiError(400, "content_policy_violation", "Input violates content policy.")
    return event
