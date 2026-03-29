from __future__ import annotations

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.entities import User, WorkspaceMember, WorkspaceRole
from app.tests.test_phase2_content_planning import (
    _create_and_assign_presets,
    _prepare_script,
    _scene_segment_write,
)


def _login(client, *, email: str, password: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def _seed_workspace_user(
    *,
    workspace_id: str,
    email: str,
    password: str,
    role: WorkspaceRole,
    full_name: str,
) -> dict[str, str]:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        session.flush()
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role,
            is_default=False,
        )
        session.add(member)
        session.commit()
        return {"user_id": str(user.id), "member_id": str(member.id)}
    finally:
        session.close()


def test_phase6_brand_kits_workspace_admin_and_webhooks(authenticated_client, seeded_auth):
    visual, voice = _create_and_assign_presets(authenticated_client, seeded_auth["project_id"])

    brand_kit = authenticated_client.post(
        "/api/v1/brand-kits",
        json={
            "name": "North Star Glow System",
            "description": "Studio-wide skincare launch defaults.",
            "status": "active",
            "enforcement_mode": "enforced",
            "is_default": True,
            "default_visual_preset_id": visual["id"],
            "default_voice_preset_id": voice["id"],
            "required_terms": ["glow"],
            "banned_terms": ["cheap"],
            "subtitle_style_override": {"font_size": 62, "placement": {"y_pct": 76}},
            "export_profile_override": {"video_bitrate_kbps": 15000},
            "audio_mix_profile_override": {"music_gain_db": -17.0},
            "brand_rules": {"tone": "premium"},
        },
    )
    assert brand_kit.status_code == 200
    brand_kit_payload = brand_kit.json()
    assert brand_kit_payload["version"] == 1

    project = authenticated_client.post(
        "/api/v1/projects",
        json={
            "title": "Brand Kit Project",
            "client": "North Star",
            "duration_target_sec": 90,
            "brand_kit_id": brand_kit_payload["id"],
        },
    )
    assert project.status_code == 200
    project_payload = project.json()
    assert project_payload["brand_kit_id"] == brand_kit_payload["id"]
    assert project_payload["default_visual_preset_id"] == visual["id"]
    assert project_payload["default_voice_preset_id"] == voice["id"]
    assert project_payload["subtitle_style_profile"]["font_size"] == 62
    assert project_payload["export_profile"]["video_bitrate_kbps"] == 15000

    blocked_brief = authenticated_client.post(
        f"/api/v1/projects/{project_payload['id']}/brief",
        json={
            "objective": "Launch a premium serum with a scientific tone.",
            "hook": "Show the serum texture before the user can scroll away.",
            "target_audience": "Women 22-34 who follow skincare creators.",
            "call_to_action": "Try the 14-day trial.",
            "brand_north_star": "Premium, clinical, calm.",
            "guardrails": ["Avoid exaggerated claims."],
            "must_include": ["Peptide callout."],
            "approval_steps": ["Client review."],
        },
    )
    assert blocked_brief.status_code == 400
    assert blocked_brief.json()["error"]["code"] == "brand_kit_violation"
    assert blocked_brief.json()["details"]["missing_terms"] == ["glow"]

    valid_brief = authenticated_client.post(
        f"/api/v1/projects/{project_payload['id']}/brief",
        json={
            "objective": "Launch a premium glow serum with a scientific tone.",
            "hook": "Show the glow texture before the user can scroll away.",
            "target_audience": "Women 22-34 who follow skincare creators.",
            "call_to_action": "Try the 14-day glow trial.",
            "brand_north_star": "Premium, clinical, calm.",
            "guardrails": ["Avoid exaggerated claims."],
            "must_include": ["Glow peptide callout."],
            "approval_steps": ["Client review."],
        },
    )
    assert valid_brief.status_code == 200

    member = authenticated_client.post(
        "/api/v1/workspace/members",
        json={
            "email": "studio-ops@example.com",
            "full_name": "Studio Ops",
            "role": "member",
        },
    )
    assert member.status_code == 200

    members = authenticated_client.get("/api/v1/workspace/members")
    assert members.status_code == 200
    assert any(item["email"] == "studio-ops@example.com" for item in members.json())

    api_key = authenticated_client.post(
        "/api/v1/workspace/api-keys",
        json={"name": "Zapier Bridge", "role_scope": "member"},
    )
    assert api_key.status_code == 200
    api_key_payload = api_key.json()
    assert api_key_payload["api_key"].startswith("rgwk_")

    api_keys = authenticated_client.get("/api/v1/workspace/api-keys")
    assert api_keys.status_code == 200
    assert "api_key" not in api_keys.json()[0]

    webhook = authenticated_client.post(
        "/api/v1/workspace/webhooks",
        json={
            "name": "Studio Sink",
            "target_url": "https://example.com/hooks/reels",
            "event_types": ["workspace.membership_created", "reviews.created"],
        },
    )
    assert webhook.status_code == 200
    webhook_payload = webhook.json()
    assert webhook_payload["signing_secret"]

    webhook_test = authenticated_client.post(
        f"/api/v1/workspace/webhooks/{webhook_payload['id']}:test"
    )
    assert webhook_test.status_code == 200
    assert webhook_test.json()["replay_id"]
    assert webhook_test.json()["signature"]

    deliveries = authenticated_client.get("/api/v1/workspace/webhook-deliveries")
    assert deliveries.status_code == 200
    assert any(item["id"] == webhook_test.json()["id"] for item in deliveries.json())

    audit = authenticated_client.get("/api/v1/workspace/audit-events")
    assert audit.status_code == 200
    event_types = {entry["event_type"] for entry in audit.json()}
    assert "brand_kits.created" in event_types
    assert "workspace.api_key_created" in event_types
    assert "workspace.membership_created" in event_types


def test_phase6_member_conflicts_comments_and_reviews(client, seeded_auth):
    member = _seed_workspace_user(
        workspace_id=seeded_auth["workspace_id"],
        email="editor@example.com",
        password="EditorPass123!",
        role=WorkspaceRole.member,
        full_name="Editor User",
    )
    reviewer = _seed_workspace_user(
        workspace_id=seeded_auth["workspace_id"],
        email="reviewer@example.com",
        password="ReviewerPass123!",
        role=WorkspaceRole.reviewer,
        full_name="Reviewer User",
    )

    _login(client, email="admin@example.com", password="ChangeMe123!")
    project_id = seeded_auth["project_id"]
    visual, _voice = _create_and_assign_presets(client, project_id)
    script_version_id = _prepare_script(client, project_id)

    preset_update = client.patch(
        f"/api/v1/presets/visual/{visual['id']}",
        json={"version": visual["version"], "style_descriptor": "Sharper macro lighting."},
    )
    assert preset_update.status_code == 200
    updated_preset = preset_update.json()
    assert updated_preset["version"] == visual["version"] + 1

    _login(client, email="editor@example.com", password="EditorPass123!")

    blocked_workspace_admin = client.get("/api/v1/workspace/api-keys")
    assert blocked_workspace_admin.status_code == 403

    preset_conflict = client.patch(
        f"/api/v1/presets/visual/{visual['id']}",
        json={"version": visual["version"], "style_descriptor": "Member stale update."},
    )
    assert preset_conflict.status_code == 409
    assert preset_conflict.json()["error"]["code"] == "visual_preset_conflict"

    preset_success = client.patch(
        f"/api/v1/presets/visual/{visual['id']}",
        json={"version": updated_preset["version"], "style_descriptor": "Member approved lighting."},
    )
    assert preset_success.status_code == 200

    scripts = client.get(f"/api/v1/projects/{project_id}/scripts")
    assert scripts.status_code == 200
    script_payload = scripts.json()[0]
    lines = list(script_payload["lines"])
    lines[0]["narration"] = f"{lines[0]['narration']} Glow starts on frame one."
    patched_script = client.patch(
        f"/api/v1/projects/{project_id}/scripts/{script_version_id}",
        json={
            "version": script_payload["version"],
            "lines": lines,
            "metadata": {"edit_reason": "Tighten opener"},
        },
    )
    assert patched_script.status_code == 200
    patched_script_payload = patched_script.json()

    _login(client, email="reviewer@example.com", password="ReviewerPass123!")

    comment = client.post(
        "/api/v1/comments",
        json={
            "project_id": project_id,
            "target_type": "script_version",
            "target_id": patched_script_payload["id"],
            "body": "The opener works. Approve once legal phrasing is confirmed.",
        },
    )
    assert comment.status_code == 200

    review = client.post(
        "/api/v1/reviews",
        json={
            "project_id": project_id,
            "target_type": "script_version",
            "target_id": patched_script_payload["id"],
            "requested_version": patched_script_payload["version"],
            "assigned_to_user_id": reviewer["user_id"],
            "request_notes": "Final script approval.",
        },
    )
    assert review.status_code == 200

    resolved_comment = client.post(
        f"/api/v1/comments/{comment.json()['id']}:resolve",
        json={"note": "Approved in review."},
    )
    assert resolved_comment.status_code == 200
    assert resolved_comment.json()["resolved_at"] is not None

    approved_review = client.post(
        f"/api/v1/reviews/{review.json()['id']}:approve",
        json={"decision_notes": "Looks good."},
    )
    assert approved_review.status_code == 200
    assert approved_review.json()["status"] == "approved"

    project_detail = client.get(f"/api/v1/projects/{project_id}")
    assert project_detail.status_code == 200
    assert project_detail.json()["active_script_version"]["id"] == patched_script_payload["id"]
    assert project_detail.json()["active_script_version"]["approval_state"] == "approved"

    _login(client, email="editor@example.com", password="EditorPass123!")

    scene_plan_job = client.post(
        f"/api/v1/projects/{project_id}/scene-plan:generate",
        headers={"Idempotency-Key": "phase6-scene-plan"},
    )
    assert scene_plan_job.status_code == 202

    scene_plans = client.get(f"/api/v1/projects/{project_id}/scene-plans")
    assert scene_plans.status_code == 200
    scene_plan = scene_plans.json()[0]
    scene_plan_detail = client.get(f"/api/v1/projects/{project_id}/scene-plans/{scene_plan['id']}")
    assert scene_plan_detail.status_code == 200

    updated_segments = [_scene_segment_write(segment) for segment in scene_plan_detail.json()["segments"]]
    updated_segments[0]["title"] = "Member revision"
    updated_scene_plan = client.patch(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan['id']}",
        json={
            "version": scene_plan_detail.json()["version"],
            "visual_preset_id": scene_plan_detail.json()["visual_preset_id"],
            "voice_preset_id": scene_plan_detail.json()["voice_preset_id"],
            "segments": updated_segments,
        },
    )
    assert updated_scene_plan.status_code == 200
    assert updated_scene_plan.json()["version"] == scene_plan_detail.json()["version"] + 1

    stale_scene_plan = client.patch(
        f"/api/v1/projects/{project_id}/scene-plans/{scene_plan['id']}",
        json={
            "version": scene_plan_detail.json()["version"],
            "visual_preset_id": scene_plan_detail.json()["visual_preset_id"],
            "voice_preset_id": scene_plan_detail.json()["voice_preset_id"],
            "segments": updated_segments,
        },
    )
    assert stale_scene_plan.status_code == 409
    assert stale_scene_plan.json()["error"]["code"] == "scene_plan_conflict"
