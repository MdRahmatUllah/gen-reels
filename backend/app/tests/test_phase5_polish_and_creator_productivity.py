from __future__ import annotations

from app.tests.test_phase2_content_planning import _create_and_assign_presets, _save_brief
from app.tests.test_phase3_render_mvp import _prepare_approved_scene_plan
from app.tests.test_phase4_reliability_and_billing import _complete_render


def test_phase5_template_clone_and_project_polish_profiles(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    _save_brief(authenticated_client, project_id)
    visual, voice = _create_and_assign_presets(authenticated_client, project_id)

    update_project = authenticated_client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "subtitle_style_profile": {
                "font_size": 64,
                "placement": {"y_pct": 78},
                "text_color": "#FFFAF0",
            },
            "export_profile": {
                "video_bitrate_kbps": 12000,
                "caption_burn_in": True,
            },
            "audio_mix_profile": {
                "crossfade_duration_seconds": 0.35,
                "music_gain_db": -18.0,
            },
        },
    )
    assert update_project.status_code == 200

    template = authenticated_client.post(
        f"/api/v1/templates/from-project/{project_id}",
        json={"name": "Skincare Launch Template", "description": "Best-performing launch defaults."},
    )
    assert template.status_code == 200
    template_payload = template.json()
    assert template_payload["latest_version"] is not None

    clone = authenticated_client.post(
        f"/api/v1/templates/{template_payload['id']}:create-project",
        json={"title": "Skincare Launch Clone", "client": "Clone Client"},
    )
    assert clone.status_code == 200
    clone_payload = clone.json()
    cloned_project = clone_payload["project"]
    assert cloned_project["source_template_version_id"] == template_payload["latest_version"]["id"]
    assert cloned_project["default_visual_preset_id"] == visual["id"]
    assert cloned_project["default_voice_preset_id"] == voice["id"]
    assert cloned_project["subtitle_style_profile"]["font_size"] == 64
    assert cloned_project["subtitle_style_profile"]["placement"]["y_pct"] == 78
    assert cloned_project["export_profile"]["video_bitrate_kbps"] == 12000
    assert cloned_project["audio_mix_profile"]["crossfade_duration_seconds"] == 0.35
    assert clone_payload["brief"] is not None
    assert clone_payload["brief"]["objective"] == "Launch a premium serum with a scientific but emotional tone."

    detail = authenticated_client.get(f"/api/v1/projects/{cloned_project['id']}")
    assert detail.status_code == 200
    assert detail.json()["active_brief"]["version_number"] == 1


def test_phase5_asset_library_reuse_profiles_and_lineage(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    project_update = authenticated_client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "subtitle_style_profile": {
                "font_size": 60,
                "placement": {"y_pct": 76},
            },
            "export_profile": {
                "video_bitrate_kbps": 14000,
            },
            "audio_mix_profile": {
                "ducking_gain_db": -10.0,
                "crossfade_duration_seconds": 0.4,
            },
        },
    )
    assert project_update.status_code == 200

    scene_plan_id = _prepare_approved_scene_plan(authenticated_client, project_id)
    render_job_id = _complete_render(
        authenticated_client,
        project_id,
        scene_plan_id,
        key="phase5-render-library-lineage",
    )

    exports = authenticated_client.get(f"/api/v1/projects/{project_id}/exports")
    assert exports.status_code == 200
    export_payload = exports.json()[0]
    assert export_payload["subtitle_style_profile"]["font_size"] == 60
    assert export_payload["export_profile"]["video_bitrate_kbps"] == 14000
    assert export_payload["audio_mix_profile"]["ducking_gain_db"] == -10.0

    render_detail = authenticated_client.get(f"/api/v1/renders/{render_job_id}")
    assert render_detail.status_code == 200
    subtitle_asset = next(
        asset for asset in render_detail.json()["assets"] if asset["asset_role"] == "subtitle_file"
    )
    assert subtitle_asset["metadata_payload"]["subtitle_style_profile"]["font_size"] == 60
    music_asset = next(asset for asset in render_detail.json()["assets"] if asset["asset_role"] == "music_bed")
    assert music_asset["metadata_payload"]["audio_mix_profile"]["crossfade_duration_seconds"] == 0.4

    library = authenticated_client.get("/api/v1/assets/library")
    assert library.status_code == 200
    library_assets = library.json()
    reusable_frame = next(
        asset
        for asset in library_assets
        if asset["project_id"] == project_id and asset["asset_role"] == "scene_end_frame"
    )
    assert reusable_frame["is_library_asset"] is True
    assert reusable_frame["is_reusable"] is True
    assert reusable_frame["continuity_score"] is not None

    clone_project = authenticated_client.post(
        "/api/v1/projects",
        json={"title": "Reuse Target", "client": "North Star Studio", "duration_target_sec": 90},
    )
    assert clone_project.status_code == 200
    clone_project_id = clone_project.json()["id"]

    reuse = authenticated_client.post(
        f"/api/v1/assets/{reusable_frame['id']}:reuse",
        json={
            "project_id": clone_project_id,
            "attach_as": "library_copy",
            "library_label": "Carryover Hero Frame",
        },
    )
    assert reuse.status_code == 200
    reused_asset = reuse.json()
    assert reused_asset["project_id"] == clone_project_id
    assert reused_asset["reused_from_asset_id"] == reusable_frame["id"]
    assert reused_asset["library_label"] == "Carryover Hero Frame"

    switch_secondary = authenticated_client.post(
        "/api/v1/auth/workspace/select",
        json={"workspace_id": seeded_auth["secondary_workspace_id"]},
    )
    assert switch_secondary.status_code == 200

    secondary_project = authenticated_client.post(
        "/api/v1/projects",
        json={"title": "Secondary Workspace Project", "client": "Studio Tide", "duration_target_sec": 90},
    )
    assert secondary_project.status_code == 200

    blocked_reuse = authenticated_client.post(
        f"/api/v1/assets/{reusable_frame['id']}:reuse",
        json={"project_id": secondary_project.json()["id"], "attach_as": "library_copy"},
    )
    assert blocked_reuse.status_code == 404
    assert blocked_reuse.json()["error"]["code"] == "asset_not_found"

    switch_primary = authenticated_client.post(
        "/api/v1/auth/workspace/select",
        json={"workspace_id": seeded_auth["workspace_id"]},
    )
    assert switch_primary.status_code == 200

    lineage = authenticated_client.get(f"/api/v1/projects/{project_id}/lineage")
    assert lineage.status_code == 200
    lineage_payload = lineage.json()
    prompt_roles = {entry["prompt_role"] for entry in lineage_payload["prompt_history"]}
    assert {
        "scene_start_frame",
        "scene_end_frame",
        "scene_video",
        "narration_generation",
        "final_composition_manifest",
    }.issubset(prompt_roles)
    assert any(asset["id"] == reusable_frame["id"] for asset in lineage_payload["library_assets"])
    assert lineage_payload["exports"]
