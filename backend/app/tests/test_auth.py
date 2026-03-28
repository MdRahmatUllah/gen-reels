from __future__ import annotations

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.entities import PasswordResetToken


def test_login_session_refresh_and_workspace_switch(client, seeded_auth):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["active_workspace_id"] == seeded_auth["workspace_id"]
    assert len(payload["workspaces"]) == 2

    session_response = client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["user"]["email"] == "admin@example.com"

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200

    switch = client.post(
        "/api/v1/auth/workspace/select",
        json={"workspace_id": seeded_auth["secondary_workspace_id"]},
    )
    assert switch.status_code == 200
    assert switch.json()["active_workspace_id"] == seeded_auth["secondary_workspace_id"]

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200


def test_password_reset_flow(client, seeded_auth):
    request = client.post("/api/v1/auth/password-reset/request", json={"email": "admin@example.com"})
    assert request.status_code == 202

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        token_row = session.query(PasswordResetToken).first()
        assert token_row is not None
    finally:
        session.close()
