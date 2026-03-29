from __future__ import annotations


def test_notifications_preferences_and_auth_config(authenticated_client, seeded_auth):
    preferences = authenticated_client.get("/api/v1/notifications/preferences")
    assert preferences.status_code == 200
    assert preferences.json()["render_email_enabled"] is True

    updated_preferences = authenticated_client.put(
        "/api/v1/notifications/preferences",
        json={"render_email_enabled": False, "planning_email_enabled": False},
    )
    assert updated_preferences.status_code == 200
    assert updated_preferences.json()["render_email_enabled"] is False
    assert updated_preferences.json()["planning_email_enabled"] is False

    auth_configuration = authenticated_client.post(
        "/api/v1/workspace/auth-configurations",
        json={
            "provider_type": "oidc",
            "display_name": "Workspace OIDC",
            "config_public": {
                "issuer": "https://issuer.example.com",
                "client_id": "workspace-client",
            },
            "secret_config": {"client_secret": "top-secret"},
            "is_enabled": True,
        },
    )
    assert auth_configuration.status_code == 200
    assert auth_configuration.json()["provider_type"] == "oidc"
    assert auth_configuration.json()["last_validation_error"] is None

    auth_configurations = authenticated_client.get("/api/v1/workspace/auth-configurations")
    assert auth_configurations.status_code == 200
    assert len(auth_configurations.json()) == 1


def test_quota_headers_notifications_and_worker_alias(authenticated_client, seeded_auth):
    session_response = authenticated_client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.headers["X-Credits-Remaining"] == "1000"
    assert session_response.headers["X-Credits-Reserved"] == "0"
    assert session_response.headers["X-Quota-Renders-Limit"] == "100"

    api_key_response = authenticated_client.post(
        "/api/v1/workspace/api-keys",
        json={"name": "Worker Alias Key", "role_scope": "member"},
    )
    assert api_key_response.status_code == 200
    api_key = api_key_response.json()["api_key"]
    assert api_key.startswith("rg_")

    register = authenticated_client.post(
        "/api/v1/workers/register",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"name": "Alias Worker", "supports_tts": True},
    )
    assert register.status_code == 200
    worker = register.json()

    heartbeat = authenticated_client.post(
        f"/api/v1/workers/{worker['id']}/heartbeat",
        headers={"Authorization": f"Bearer {worker['worker_token']}"},
        json={"metadata_payload": {"uptime": "healthy"}},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["name"] == "Alias Worker"

