from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt

from app.core.errors import ApiError


def _issued_at() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    *,
    private_key: str,
    user_id: str,
    email: str,
    workspace_id: str,
    workspace_role: str,
    session_id: str,
    expires_in_minutes: int,
) -> str:
    issued_at = _issued_at()
    payload = {
        "sub": user_id,
        "email": email,
        "workspace_id": workspace_id,
        "workspace_role": workspace_role,
        "session_id": session_id,
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def create_refresh_token(
    *,
    private_key: str,
    user_id: str,
    session_id: str,
    expires_in_days: int,
) -> str:
    issued_at = _issued_at()
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(days=expires_in_days)).timestamp()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def decode_token(token: str, public_key: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "token_expired", "Your session has expired.") from exc
    except jwt.PyJWTError as exc:
        raise ApiError(401, "invalid_token", "Invalid authentication token.") from exc

    if payload.get("type") != expected_type:
        raise ApiError(401, "invalid_token", "Invalid authentication token.")

    return payload
