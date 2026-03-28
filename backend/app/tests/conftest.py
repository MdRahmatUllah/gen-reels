from __future__ import annotations

from pathlib import Path

import fakeredis
import pytest
import redis as redis_module
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import configure_session_factory, get_engine, get_session_factory
from app.main import create_app
from app.models.entities import Project, User, Workspace, WorkspaceMember, WorkspaceRole


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "test.db"
    database_url = f"sqlite:///{database_path}"
    fake_redis = fakeredis.FakeRedis(decode_responses=True)

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("USE_STUB_PROVIDERS", "true")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("REDIS_URL", "redis://unused/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://unused/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://unused/2")
    monkeypatch.setattr(redis_module.Redis, "from_url", lambda *args, **kwargs: fake_redis)

    get_settings.cache_clear()
    configure_session_factory(database_url)
    engine = get_engine(database_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(engine)
    get_settings.cache_clear()


@pytest.fixture
def seeded_auth(client: TestClient):
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        user = User(
            email="admin@example.com",
            full_name="Reels Admin",
            password_hash=hash_password("ChangeMe123!"),
            is_admin=True,
        )
        workspace = Workspace(
            name="North Star Studio",
            slug="north-star-studio",
            plan_name="Pro Studio",
            seats=5,
            credits_remaining=1000,
            credits_total=1000,
            monthly_budget_cents=500000,
        )
        secondary = Workspace(
            name="Studio Tide",
            slug="studio-tide",
            plan_name="Growth",
            seats=3,
            credits_remaining=500,
            credits_total=500,
            monthly_budget_cents=250000,
        )
        session.add_all([user, workspace, secondary])
        session.flush()
        session.add_all(
            [
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role=WorkspaceRole.admin,
                    is_default=True,
                ),
                WorkspaceMember(
                    workspace_id=secondary.id,
                    user_id=user.id,
                    role=WorkspaceRole.admin,
                    is_default=False,
                ),
            ]
        )
        project = Project(
            workspace_id=workspace.id,
            owner_user_id=user.id,
            title="Aurora Serum Launch",
            client="North Star Studio",
            aspect_ratio="9:16",
            duration_target_sec=90,
        )
        session.add(project)
        session.commit()
        return {
            "user_id": str(user.id),
            "workspace_id": str(workspace.id),
            "secondary_workspace_id": str(secondary.id),
            "project_id": str(project.id),
        }
    finally:
        session.close()


@pytest.fixture
def authenticated_client(client: TestClient, seeded_auth):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200
    return client
