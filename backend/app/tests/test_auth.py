from __future__ import annotations

from cryptography.fernet import Fernet

from app.core.config import Settings, get_settings
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


def test_disable_browser_auth_defaults_to_development():
    development_settings = Settings(
        environment="development",
        app_encryption_key=Fernet.generate_key().decode("utf-8"),
    )
    assert development_settings.disable_browser_auth_resolved is True

    test_settings = Settings(environment="test")
    assert test_settings.disable_browser_auth_resolved is False


def test_browser_auth_disabled_returns_synthetic_session_without_login(client, seeded_auth):
    client.app.state.settings.disable_browser_auth = True

    session_response = client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["user"]["email"] == "admin@example.com"
    assert session_response.json()["active_workspace_id"] == seeded_auth["workspace_id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "bogus@example.com", "password": "LongEnough123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "admin@example.com"

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["active_workspace_id"] == seeded_auth["workspace_id"]

    projects_response = client.get("/api/v1/projects")
    assert projects_response.status_code == 200
    assert len(projects_response.json()) == 1


def test_browser_auth_disabled_persists_workspace_selection_with_cookie(client, seeded_auth):
    client.app.state.settings.disable_browser_auth = True
    settings = client.app.state.settings

    switch_response = client.post(
        "/api/v1/auth/workspace/select",
        json={"workspace_id": seeded_auth["secondary_workspace_id"]},
    )
    assert switch_response.status_code == 200
    assert switch_response.json()["active_workspace_id"] == seeded_auth["secondary_workspace_id"]
    assert switch_response.cookies.get(settings.dev_workspace_cookie_name) == seeded_auth["secondary_workspace_id"]

    session_response = client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["active_workspace_id"] == seeded_auth["secondary_workspace_id"]
