from __future__ import annotations


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


def _create_and_assign_presets(client, project_id: str) -> tuple[dict, dict]:
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
    return visual.json(), voice.json()


def _prepare_script(client, project_id: str) -> str:
    _save_brief(client, project_id)
    ideas_job = client.post(
        f"/api/v1/projects/{project_id}/ideas:generate",
        headers={"Idempotency-Key": "ideas-phase2"},
    )
    assert ideas_job.status_code == 202
    ideas = client.get(f"/api/v1/projects/{project_id}/ideas")
    assert ideas.status_code == 200
    selected_idea_id = ideas.json()[0]["candidates"][0]["id"]
    select_response = client.post(f"/api/v1/projects/{project_id}/ideas/{selected_idea_id}:select")
    assert select_response.status_code == 200
    script_job = client.post(
        f"/api/v1/projects/{project_id}/scripts:generate",
        headers={"Idempotency-Key": "script-phase2"},
    )
    assert script_job.status_code == 202
    scripts = client.get(f"/api/v1/projects/{project_id}/scripts")
    assert scripts.status_code == 200
    return scripts.json()[0]["id"]


def _scene_segment_write(segment: dict) -> dict:
    return {
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


def test_phase2_preset_crud_and_project_defaults(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    visual, voice = _create_and_assign_presets(authenticated_client, project_id)

    listed_visual = authenticated_client.get("/api/v1/presets/visual")
    assert listed_visual.status_code == 200
    assert listed_visual.json()[0]["id"] == visual["id"]

    listed_voice = authenticated_client.get("/api/v1/presets/voice")
    assert listed_voice.status_code == 200
    assert listed_voice.json()[0]["id"] == voice["id"]

    patched_visual = authenticated_client.patch(
        f"/api/v1/presets/visual/{visual['id']}",
        json={"style_descriptor": "Sharper macro lighting.", "is_archived": True},
    )
    assert patched_visual.status_code == 200
    assert patched_visual.json()["is_archived"] is True

    patched_voice = authenticated_client.patch(
        f"/api/v1/presets/voice/{voice['id']}",
        json={"pace_multiplier": 1.1},
    )
    assert patched_voice.status_code == 200
    assert patched_voice.json()["pace_multiplier"] == 1.1

    detail = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["project"]["default_visual_preset_id"] == visual["id"]
    assert detail.json()["project"]["default_voice_preset_id"] == voice["id"]


def test_scene_plan_generation_requires_approved_script(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    _create_and_assign_presets(authenticated_client, project_id)
    _prepare_script(authenticated_client, project_id)

    scene_plan_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plan:generate",
        headers={"Idempotency-Key": "scene-plan-missing-approval"},
    )
    assert scene_plan_job.status_code == 400
    assert scene_plan_job.json()["error"]["code"] == "script_not_approved"


def test_scene_plan_flow_prompt_pair_validation_and_versioning(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    _create_and_assign_presets(authenticated_client, project_id)
    script_version_id = _prepare_script(authenticated_client, project_id)

    approve_script = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scripts/{script_version_id}:approve"
    )
    assert approve_script.status_code == 200
    assert approve_script.json()["approval_state"] == "approved"

    first_scene_plan_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plan:generate",
        headers={"Idempotency-Key": "scene-plan-1"},
    )
    assert first_scene_plan_job.status_code == 202
    second_scene_plan_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plan:generate",
        headers={"Idempotency-Key": "scene-plan-1"},
    )
    assert second_scene_plan_job.status_code == 202
    assert second_scene_plan_job.json()["job_id"] == first_scene_plan_job.json()["job_id"]

    scene_plans = authenticated_client.get(f"/api/v1/projects/{project_id}/scene-plans")
    assert scene_plans.status_code == 200
    assert len(scene_plans.json()) == 1
    scene_plan = scene_plans.json()[0]
    assert scene_plan["scene_count"] >= 6
    scene_plan_id = scene_plan["id"]

    prompt_pair_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:generate-prompt-pairs",
        headers={"Idempotency-Key": "prompt-pairs-1"},
    )
    assert prompt_pair_job.status_code == 202

    scene_plan_detail = authenticated_client.get(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}"
    )
    assert scene_plan_detail.status_code == 200
    assert all(segment["start_image_prompt"] for segment in scene_plan_detail.json()["segments"])
    assert all(segment["end_image_prompt"] for segment in scene_plan_detail.json()["segments"])

    broken_segments = [_scene_segment_write(segment) for segment in scene_plan_detail.json()["segments"]]
    broken_segments[0]["start_image_prompt"] = ""
    broken_segments[0]["end_image_prompt"] = ""
    broken_patch = authenticated_client.patch(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}",
        json={"segments": broken_segments},
    )
    assert broken_patch.status_code == 200

    invalid_approval = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:approve"
    )
    assert invalid_approval.status_code == 400
    assert invalid_approval.json()["error"]["code"] == "prompt_pairs_incomplete"

    fixed_segments = [_scene_segment_write(segment) for segment in scene_plan_detail.json()["segments"]]
    fixed_segments[0]["title"] = "Revised hook scene"
    fixed_patch = authenticated_client.patch(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}",
        json={"segments": fixed_segments},
    )
    assert fixed_patch.status_code == 200
    assert fixed_patch.json()["source_type"] == "manual"

    approved_scene_plan = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:approve"
    )
    assert approved_scene_plan.status_code == 200
    assert approved_scene_plan.json()["approval_state"] == "approved"
    assert approved_scene_plan.json()["consistency_pack_id"] is not None

    project_detail = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert project_detail.status_code == 200
    assert project_detail.json()["project"]["active_scene_plan_id"] == scene_plan_id
    assert project_detail.json()["active_scene_plan"]["approval_state"] == "approved"

    cloned_segments = [_scene_segment_write(segment) for segment in approved_scene_plan.json()["segments"]]
    cloned_segments[0]["title"] = "Post approval revision"
    new_version = authenticated_client.patch(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan_id}",
        json={"segments": cloned_segments},
    )
    assert new_version.status_code == 200
    assert new_version.json()["version_number"] == 2
    assert new_version.json()["parent_scene_plan_id"] == scene_plan_id
    assert new_version.json()["approval_state"] == "draft"
