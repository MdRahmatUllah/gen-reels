from __future__ import annotations

from pathlib import Path


def _save_brief(client, project_id: str):
    response = client.post(
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
    assert response.status_code == 200


def _create_and_assign_presets(client, project_id: str):
    visual = client.post(
        "/api/v1/presets/visual",
        json={
            "name": "Clinical Luxe",
            "description": "Premium skincare macro look.",
            "prompt_prefix": "Editorial beauty photography.",
            "style_descriptor": "Clean highlights and expensive texture detail.",
            "negative_prompt": "No clutter, no extra hands.",
            "camera_defaults": "85mm macro, soft diffused lighting.",
            "color_palette": "Ivory, silver, champagne.",
            "reference_notes": "Focus on serum texture and premium packaging.",
        },
    )
    assert visual.status_code == 200

    voice = client.post(
        "/api/v1/presets/voice",
        json={
            "name": "Measured Expert",
            "description": "Clear skincare educator pacing.",
            "provider_voice": "alloy",
            "tone_descriptor": "Measured, confident, warm.",
            "language_code": "en-US",
            "pace_multiplier": 1.0,
        },
    )
    assert voice.status_code == 200

    assign = client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "default_visual_preset_id": visual.json()["id"],
            "default_voice_preset_id": voice.json()["id"],
        },
    )
    assert assign.status_code == 200


def _prepare_approved_scene_plan(client, project_id: str) -> str:
    _save_brief(client, project_id)
    _create_and_assign_presets(client, project_id)

    ideas_job = client.post(
        f"/api/v1/projects/{project_id}/ideas:generate",
        headers={"Idempotency-Key": "phase3-ideas"},
    )
    assert ideas_job.status_code == 202
    ideas = client.get(f"/api/v1/projects/{project_id}/ideas")
    selected_idea_id = ideas.json()[0]["candidates"][0]["id"]
    select_response = client.post(f"/api/v1/projects/{project_id}/ideas/{selected_idea_id}:select")
    assert select_response.status_code == 200

    script_job = client.post(
        f"/api/v1/projects/{project_id}/scripts:generate",
        headers={"Idempotency-Key": "phase3-script"},
    )
    assert script_job.status_code == 202
    scripts = client.get(f"/api/v1/projects/{project_id}/scripts")
    script_version_id = scripts.json()[0]["id"]
    approve_script = client.post(f"/api/v1/projects/{project_id}/scripts/{script_version_id}:approve")
    assert approve_script.status_code == 200

    scene_plan_job = client.post(
        f"/api/v1/projects/{project_id}/scene-plan:generate",
        headers={"Idempotency-Key": "phase3-scene-plan"},
    )
    assert scene_plan_job.status_code == 202
    scene_plans = client.get(f"/api/v1/projects/{project_id}/scene-plans")
    scene_plan_id = scene_plans.json()[0]["id"]

    prompt_pairs = client.post(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:generate-prompt-pairs",
        headers={"Idempotency-Key": "phase3-prompt-pairs"},
    )
    assert prompt_pairs.status_code == 202

    approve_scene_plan = client.post(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:approve"
    )
    assert approve_scene_plan.status_code == 200
    return scene_plan_id


def test_phase3_render_review_and_export_flow(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    scene_plan_id = _prepare_approved_scene_plan(authenticated_client, project_id)

    render_response = authenticated_client.post(
        f"/api/v1/projects/{project_id}/renders",
        headers={"Idempotency-Key": "render-1"},
        json={"scene_plan_id": scene_plan_id, "allow_export_without_music": True},
    )
    assert render_response.status_code == 202
    render_job_id = render_response.json()["job_id"]

    repeat_render = authenticated_client.post(
        f"/api/v1/projects/{project_id}/renders",
        headers={"Idempotency-Key": "render-1"},
        json={"scene_plan_id": scene_plan_id, "allow_export_without_music": True},
    )
    assert repeat_render.status_code == 202
    assert repeat_render.json()["job_id"] == render_job_id

    render_detail = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert render_detail.status_code == 200
    assert render_detail.json()["status"] == "review"
    frame_pair_steps = [
        step for step in render_detail.json()["steps"] if step["step_kind"] == "frame_pair_generation"
    ]
    assert frame_pair_steps
    assert all(step["status"] == "review" for step in frame_pair_steps)

    regenerate = authenticated_client.post(
        f"/api/v1/renders/{render_job_id}/steps/{frame_pair_steps[0]['id']}:regenerate-frame-pair"
    )
    assert regenerate.status_code == 200
    assert regenerate.json()["status"] == "review"

    refreshed_detail = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    refreshed_steps = [
        step for step in refreshed_detail.json()["steps"] if step["step_kind"] == "frame_pair_generation"
    ]
    for step in refreshed_steps:
        approve = authenticated_client.post(
            f"/api/v1/renders/{render_job_id}/steps/{step['id']}:approve-frame-pair"
        )
        assert approve.status_code == 200

    completed_render = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert completed_render.status_code == 200
    assert completed_render.json()["status"] == "completed"
    assert completed_render.json()["exports"]
    assert any(asset["asset_role"] == "final_export" for asset in completed_render.json()["assets"])
    assert any(step["step_kind"] == "composition" for step in completed_render.json()["steps"])

    exports = authenticated_client.get(f"/api/v1/projects/{project_id}/exports")
    assert exports.status_code == 200
    assert len(exports.json()) == 1
    export = exports.json()[0]
    assert export["render_job_id"] == render_job_id

    signed_url = authenticated_client.post(f"/api/v1/assets/{export['asset_id']}/signed-url")
    assert signed_url.status_code == 200
    assert Path(signed_url.json()["url"]).exists()

    events = authenticated_client.get(f"/api/v1/renders/{render_job_id}/events")
    assert events.status_code == 200
    event_types = [event["event_type"] for event in events.json()]
    assert "render.created" in event_types
    assert "render.completed" in event_types
