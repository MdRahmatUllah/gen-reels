from __future__ import annotations

from app.core.errors import AdapterError
from app.integrations.azure import StubTextProvider
from app.tests.test_phase2_content_planning import _create_and_assign_presets, _save_brief


def test_quick_start_studio_default_bootstraps_project(authenticated_client, seeded_auth):
    response = authenticated_client.post(
        "/api/v1/projects:quick-start",
        json={
            "idea_prompt": "Create a premium skincare reel about a serum that gives a healthy glow in the first 3 seconds.",
            "starter_mode": "studio_default",
        },
        headers={"Idempotency-Key": "quick-start-default"},
    )
    assert response.status_code == 200
    payload = response.json()
    project_id = payload["project"]["id"]

    status = authenticated_client.get(f"/api/v1/projects/{project_id}/quick-start-status")
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["job"]["status"] == "completed"
    assert status_payload["completed_steps"] == [
        "brief_generation",
        "idea_generation",
        "script_generation",
        "scene_plan_generation",
        "prompt_pair_generation",
    ]
    assert status_payload["redirect_path"] == f"/app/projects/{project_id}/scenes"

    detail = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["active_brief"] is not None
    assert detail_payload["selected_idea"] is not None
    assert detail_payload["active_script_version"]["approval_state"] == "approved"
    assert detail_payload["active_scene_plan"]["approval_state"] == "approved"

    visual_presets = authenticated_client.get("/api/v1/presets/visual")
    voice_presets = authenticated_client.get("/api/v1/presets/voice")
    assert visual_presets.status_code == 200
    assert voice_presets.status_code == 200
    assert any(preset["name"] == "Studio Default Visual" for preset in visual_presets.json())
    assert any(preset["name"] == "Studio Default Voice" for preset in voice_presets.json())


def test_quick_start_template_applies_defaults_but_generates_fresh_brief(authenticated_client, seeded_auth):
    source_project_id = seeded_auth["project_id"]
    _save_brief(authenticated_client, source_project_id)
    visual, voice = _create_and_assign_presets(authenticated_client, source_project_id)

    update_project = authenticated_client.patch(
        f"/api/v1/projects/{source_project_id}",
        json={
            "subtitle_style_profile": {"font_size": 64, "placement": {"y_pct": 78}},
            "export_profile": {"video_bitrate_kbps": 14000, "caption_burn_in": True},
            "audio_mix_profile": {"crossfade_duration_seconds": 0.4},
        },
    )
    assert update_project.status_code == 200

    template = authenticated_client.post(
        f"/api/v1/templates/from-project/{source_project_id}",
        json={"name": "Launch Starter", "description": "Premium launch framing."},
    )
    assert template.status_code == 200
    template_id = template.json()["id"]

    response = authenticated_client.post(
        "/api/v1/projects:quick-start",
        json={
            "idea_prompt": "Tell the founder story of a new wellness tonic with intimate, direct-to-camera energy.",
            "starter_mode": "template",
            "template_id": template_id,
        },
        headers={"Idempotency-Key": "quick-start-template"},
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    detail = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["project"]["default_visual_preset_id"] == visual["id"]
    assert detail_payload["project"]["default_voice_preset_id"] == voice["id"]
    assert detail_payload["project"]["subtitle_style_profile"]["font_size"] == 64
    assert detail_payload["project"]["export_profile"]["video_bitrate_kbps"] == 14000
    assert detail_payload["project"]["audio_mix_profile"]["crossfade_duration_seconds"] == 0.4
    assert detail_payload["active_brief"]["objective"] != "Launch a premium serum with a scientific but emotional tone."
    assert "wellness tonic" in detail_payload["active_brief"]["objective"].lower()


def test_quick_start_idempotency_and_failure_status(authenticated_client, monkeypatch):
    original_generate_script = StubTextProvider.generate_script

    def broken_generate_script(self, *, brief_payload, selected_idea):
        raise AdapterError("deterministic_input", "quick_start_script_failed", "Script generation broke on purpose.")

    monkeypatch.setattr(StubTextProvider, "generate_script", broken_generate_script)
    try:
        first = authenticated_client.post(
            "/api/v1/projects:quick-start",
            json={
                "idea_prompt": "Make a creator-style gadget launch reel with kinetic pacing.",
                "starter_mode": "studio_default",
            },
            headers={"Idempotency-Key": "quick-start-failure"},
        )
        assert first.status_code == 200
        second = authenticated_client.post(
            "/api/v1/projects:quick-start",
            json={
                "idea_prompt": "Make a creator-style gadget launch reel with kinetic pacing.",
                "starter_mode": "studio_default",
            },
            headers={"Idempotency-Key": "quick-start-failure"},
        )
        assert second.status_code == 200
        assert first.json()["project"]["id"] == second.json()["project"]["id"]
        assert first.json()["job"]["id"] == second.json()["job"]["id"]

        project_id = first.json()["project"]["id"]
        status = authenticated_client.get(f"/api/v1/projects/{project_id}/quick-start-status")
        assert status.status_code == 200
        status_payload = status.json()
        assert status_payload["job"]["status"] == "failed"
        assert status_payload["current_step"] == "script_generation"
        assert status_payload["recovery_path"] == f"/app/projects/{project_id}/script"
        assert status_payload["job"]["error_code"] == "quick_start_script_failed"
    finally:
        monkeypatch.setattr(StubTextProvider, "generate_script", original_generate_script)
