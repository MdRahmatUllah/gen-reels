from __future__ import annotations

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.integrations.azure import STUB_MODERATION_BLOCK_SENTINEL
from app.models.entities import Workspace
from app.tests.test_phase3_render_mvp import _prepare_approved_scene_plan


def _complete_render(client, project_id: str, scene_plan_id: str, *, key: str) -> str:
    response = client.post(
        f"/api/v1/projects/{project_id}/renders",
        headers={"Idempotency-Key": key},
        json={"scene_plan_id": scene_plan_id, "allow_export_without_music": True},
    )
    assert response.status_code == 202
    render_job_id = response.json()["job_id"]
    detail = client.get(f"/api/v1/renders/{render_job_id}")
    assert detail.status_code == 200
    frame_pair_steps = [
        step for step in detail.json()["steps"] if step["step_kind"] == "frame_pair_generation"
    ]
    for step in frame_pair_steps:
        approve = client.post(f"/api/v1/renders/{render_job_id}/steps/{step['id']}:approve-frame-pair")
        assert approve.status_code == 200
    completed = client.get(f"/api/v1/renders/{render_job_id}")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    return render_job_id


def _approve_all_frame_pair_reviews(client, render_job_id: str) -> dict[str, object]:
    final_payload: dict[str, object] | None = None
    for _ in range(10):
        detail = client.get(f"/api/v1/renders/{render_job_id}")
        assert detail.status_code == 200
        final_payload = detail.json()
        if final_payload["status"] != "review":
            return final_payload
        frame_pair_steps = [
            step
            for step in final_payload["steps"]
            if step["step_kind"] == "frame_pair_generation" and step["status"] == "review"
        ]
        assert frame_pair_steps
        for step in frame_pair_steps:
            approve_step = client.post(
                f"/api/v1/renders/{render_job_id}/steps/{step['id']}:approve-frame-pair"
            )
            assert approve_step.status_code == 200
    assert final_payload is not None
    return final_payload


def test_phase4_usage_billing_and_admin_views(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    scene_plan_id = _prepare_approved_scene_plan(authenticated_client, project_id)
    render_job_id = _complete_render(authenticated_client, project_id, scene_plan_id, key="phase4-render-usage")

    usage = authenticated_client.get("/api/v1/usage")
    assert usage.status_code == 200
    usage_payload = usage.json()
    assert usage_payload["workspace_id"] == seeded_auth["workspace_id"]
    assert usage_payload["credits_remaining"] < usage_payload["credits_total"]
    assert usage_payload["month_provider_run_count"] > 0
    assert usage_payload["month_export_count"] >= 1
    ledger_kinds = {entry["kind"] for entry in usage_payload["recent_entries"]}
    assert "provider_run" in ledger_kinds
    assert "export_event" in ledger_kinds

    subscription = authenticated_client.get("/api/v1/billing/subscription")
    assert subscription.status_code == 200
    assert subscription.json()["status"] == "not_configured"

    checkout = authenticated_client.post("/api/v1/billing/checkout")
    assert checkout.status_code == 200
    assert checkout.json()["status"] == "checkout_pending"
    assert "/billing/checkout" in checkout.json()["url"]

    portal = authenticated_client.post("/api/v1/billing/portal")
    assert portal.status_code == 200
    assert "/billing/portal" in portal.json()["url"]

    admin_renders = authenticated_client.get("/api/v1/admin/renders")
    assert admin_renders.status_code == 200
    matched = next(item for item in admin_renders.json() if item["id"] == render_job_id)
    assert matched["provider_run_count"] > 0
    assert matched["latest_provider_cost_cents"] >= 0
    assert matched["step_count"] > 0

    moderation_queue = authenticated_client.get("/api/v1/admin/moderation")
    assert moderation_queue.status_code == 200
    assert moderation_queue.json() == []


def test_phase4_render_requires_sufficient_credits(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    scene_plan_id = _prepare_approved_scene_plan(authenticated_client, project_id)

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        workspace = session.get(Workspace, seeded_auth["workspace_id"])
        assert workspace is not None
        workspace.credits_remaining = 1
        session.commit()
    finally:
        session.close()

    render = authenticated_client.post(
        f"/api/v1/projects/{project_id}/renders",
        headers={"Idempotency-Key": "phase4-insufficient-credits"},
        json={"scene_plan_id": scene_plan_id, "allow_export_without_music": True},
    )
    assert render.status_code == 402
    assert render.json()["error"]["code"] == "insufficient_credits"


def test_phase4_moderation_quarantine_release_and_resume(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    scene_plan_id = _prepare_approved_scene_plan(authenticated_client, project_id)

    original_scene_plan = authenticated_client.get(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}"
    )
    assert original_scene_plan.status_code == 200
    scene_plan_payload = original_scene_plan.json()
    segments = scene_plan_payload["segments"]
    segments[0]["start_image_prompt"] = f"{STUB_MODERATION_BLOCK_SENTINEL} {segments[0]['start_image_prompt']}"

    patch_payload = {
        "visual_preset_id": scene_plan_payload["visual_preset_id"],
        "voice_preset_id": scene_plan_payload["voice_preset_id"],
        "segments": [
            {
                "scene_index": segment["scene_index"],
                "source_line_ids": segment["source_line_ids"],
                "title": segment["title"],
                "beat": segment["beat"],
                "narration_text": segment["narration_text"],
                "caption_text": segment["caption_text"],
                "visual_direction": segment["visual_direction"],
                "shot_type": segment["shot_type"],
                "motion": segment["motion"],
                "target_duration_seconds": segment["target_duration_seconds"],
                "estimated_voice_duration_seconds": segment["estimated_voice_duration_seconds"],
                "visual_prompt": segment["visual_prompt"],
                "start_image_prompt": segment["start_image_prompt"],
                "end_image_prompt": segment["end_image_prompt"],
                "transition_mode": segment["transition_mode"],
                "notes": segment["notes"],
            }
            for segment in segments
        ],
    }
    patched = authenticated_client.patch(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}",
        json=patch_payload,
    )
    assert patched.status_code == 200
    patched_scene_plan_id = patched.json()["id"]

    approve = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plans/{patched_scene_plan_id}:approve"
    )
    assert approve.status_code == 200

    render = authenticated_client.post(
        f"/api/v1/projects/{project_id}/renders",
        headers={"Idempotency-Key": "phase4-moderation-release"},
        json={"scene_plan_id": patched_scene_plan_id, "allow_export_without_music": True},
    )
    assert render.status_code == 202
    render_job_id = render.json()["job_id"]

    blocked_render = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert blocked_render.status_code == 200
    assert blocked_render.json()["status"] == "blocked"

    moderation_queue = authenticated_client.get("/api/v1/admin/moderation")
    assert moderation_queue.status_code == 200
    assert moderation_queue.json()
    moderation_event = moderation_queue.json()[0]
    assert moderation_event["review_status"] == "pending"
    assert moderation_event["asset_status"] == "quarantined"

    release = authenticated_client.post(
        f"/api/v1/admin/moderation/{moderation_event['id']}:release",
        json={"notes": "Release after manual review."},
    )
    assert release.status_code == 200
    assert release.json()["review_status"] == "released"

    render_after_release = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert render_after_release.status_code == 200
    assert render_after_release.json()["status"] == "review"

    completed_render = _approve_all_frame_pair_reviews(authenticated_client, render_job_id)
    assert completed_render["status"] == "completed"

    released_items = authenticated_client.get("/api/v1/admin/moderation", params={"review_status": "released"})
    assert released_items.status_code == 200
    assert any(item["id"] == moderation_event["id"] for item in released_items.json())
