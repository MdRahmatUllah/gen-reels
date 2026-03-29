from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.entities import LocalWorker, ProviderRun
from app.tests.test_phase3_render_mvp import _prepare_approved_scene_plan


def test_phase7_byo_execution_policy_and_usage(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]

    credential_response = authenticated_client.post(
        "/api/v1/workspace/provider-credentials",
        json={
            "name": "Workspace Azure OpenAI",
            "modality": "text",
            "provider_key": "azure_openai_text",
            "public_config": {
                "endpoint": "https://example-resource.openai.azure.com",
                "deployment": "gpt-4o",
            },
            "secret_config": {"api_key": "secret-value"},
        },
    )
    assert credential_response.status_code == 200
    credential = credential_response.json()
    assert "secret_config" not in credential

    policy_response = authenticated_client.put(
        "/api/v1/workspace/execution-policy",
        json={
            "text": {
                "mode": "byo",
                "provider_key": "azure_openai_text",
                "credential_id": credential["id"],
            }
        },
    )
    assert policy_response.status_code == 200
    assert policy_response.json()["text"]["mode"] == "byo"

    brief_response = authenticated_client.post(
        f"/api/v1/projects/{project_id}/brief",
        json={
            "objective": "Launch a premium serum with a scientific but emotional tone.",
            "hook": "Show the serum texture before the user can scroll away.",
            "target_audience": "Women 22-34 who follow skincare creators.",
            "call_to_action": "Try the 14-day glow trial.",
            "brand_north_star": "Premium, clinical, calm.",
            "guardrails": ["Avoid exaggerated claims."],
            "must_include": ["Peptide callout."],
            "approval_steps": ["Client review."],
        },
    )
    assert brief_response.status_code == 200

    ideas_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/ideas:generate",
        headers={"Idempotency-Key": "phase7-byo-ideas"},
    )
    assert ideas_job.status_code == 202

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        provider_run = session.query(ProviderRun).order_by(ProviderRun.started_at.desc()).first()
        assert provider_run is not None
        assert provider_run.execution_mode.value == "byo"
        assert provider_run.provider_credential_id is not None
    finally:
        session.close()

    usage = authenticated_client.get("/api/v1/usage")
    assert usage.status_code == 200
    assert usage.json()["month_execution_mode_summary"]["byo"]["provider_run_count"] >= 1


def test_phase7_local_worker_registration_and_health(authenticated_client):
    api_key_response = authenticated_client.post(
        "/api/v1/workspace/api-keys",
        json={"name": "Local Worker Registrar", "role_scope": "member"},
    )
    assert api_key_response.status_code == 200
    api_key = api_key_response.json()["api_key"]

    register = authenticated_client.post(
        "/api/v1/local-workers/register",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "name": "Desktop RTX Worker",
            "supports_tts": True,
            "supports_clip_retime": True,
            "metadata_payload": {"device": "RTX 4090"},
        },
    )
    assert register.status_code == 200
    worker = register.json()
    assert worker["worker_token"].startswith("rglw_")

    heartbeat = authenticated_client.post(
        f"/api/v1/local-workers/{worker['id']}/heartbeat",
        headers={"Authorization": f"Bearer {worker['worker_token']}"},
        json={"metadata_payload": {"temperature_c": 58}},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "online"

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        worker_row = session.get(LocalWorker, worker["id"])
        assert worker_row is not None
        worker_row.last_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)
        session.commit()
    finally:
        session.close()

    from app.services.routing_service import RoutingService

    session = get_session_factory(settings.database_url)()
    try:
        updated = RoutingService(session, settings).refresh_worker_statuses()
        assert updated >= 1
    finally:
        session.close()

    workers = authenticated_client.get("/api/v1/workspace/local-workers")
    assert workers.status_code == 200
    assert workers.json()[0]["status"] == "offline"


def test_phase7_local_worker_render_resume_flow(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    scene_plan_id = _prepare_approved_scene_plan(authenticated_client, project_id)

    api_key_response = authenticated_client.post(
        "/api/v1/workspace/api-keys",
        json={"name": "Narration Worker Registrar", "role_scope": "member"},
    )
    assert api_key_response.status_code == 200
    api_key = api_key_response.json()["api_key"]

    register = authenticated_client.post(
        "/api/v1/local-workers/register",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "name": "Narration Worker",
            "supports_tts": True,
            "metadata_payload": {"voice_stack": "local-xtts"},
        },
    )
    assert register.status_code == 200
    worker = register.json()
    worker_headers = {"Authorization": f"Bearer {worker['worker_token']}"}

    policy_response = authenticated_client.put(
        "/api/v1/workspace/execution-policy",
        json={
            "speech": {
                "mode": "local",
                "provider_key": "local_xtts",
            },
            "preferred_local_worker_id": worker["id"],
        },
    )
    assert policy_response.status_code == 200
    assert policy_response.json()["speech"]["mode"] == "local"

    render_response = authenticated_client.post(
        f"/api/v1/projects/{project_id}/renders",
        headers={"Idempotency-Key": "phase7-local-render"},
        json={"scene_plan_id": scene_plan_id, "allow_export_without_music": True},
    )
    assert render_response.status_code == 202
    render_job_id = render_response.json()["job_id"]

    render_detail = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert render_detail.status_code == 200
    frame_pair_steps = [
        step for step in render_detail.json()["steps"] if step["step_kind"] == "frame_pair_generation"
    ]
    assert frame_pair_steps
    for step in frame_pair_steps:
        approve = authenticated_client.post(
            f"/api/v1/renders/{render_job_id}/steps/{step['id']}:approve-frame-pair"
        )
        assert approve.status_code == 200

    for _ in range(50):
        poll = authenticated_client.get(
            f"/api/v1/local-workers/{worker['id']}/jobs/next",
            headers=worker_headers,
        )
        assert poll.status_code == 200
        job = poll.json()["job"]
        if not job:
            render_detail = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
            assert render_detail.status_code == 200
            if render_detail.json()["status"] == "completed":
                break
            continue

        assert job["modality"] == "speech"
        output = job["outputs"][0]
        Path(output["upload_url"]).write_bytes(b"stub narration")
        result = authenticated_client.post(
            f"/api/v1/local-workers/{worker['id']}/jobs/{job['render_step_id']}/result",
            headers=worker_headers,
            json={
                "status": "completed",
                "duration_seconds": 4.0,
                "outputs": [
                    {
                        "role": output["role"],
                        "bucket_name": output["bucket_name"],
                        "object_name": output["object_name"],
                        "content_type": output["content_type"],
                        "file_name": output["file_name"],
                        "metadata_payload": {"sample_rate": 16000},
                    }
                ],
                "provider_metadata": {"engine": "local-xtts"},
            },
        )
        assert result.status_code == 200
    else:
        raise AssertionError("Render did not complete within the expected local worker polling loop.")

    render_detail = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert render_detail.status_code == 200
    assert render_detail.json()["status"] == "completed"
    assert render_detail.json()["exports"]

    usage = authenticated_client.get("/api/v1/usage")
    assert usage.status_code == 200
    assert usage.json()["month_execution_mode_summary"]["local"]["provider_run_count"] >= 1
