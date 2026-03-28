from __future__ import annotations


def _save_brief(client, project_id: str):
    brief_payload = {
        "objective": "Launch a premium serum with a scientific but emotional tone.",
        "hook": "Show the serum texture before the user can scroll away.",
        "target_audience": "Women 22-34 who follow skincare creators.",
        "call_to_action": "Try the 14-day glow trial.",
        "brand_north_star": "Premium, clinical, calm.",
        "guardrails": ["Avoid exaggerated claims."],
        "must_include": ["Peptide callout."],
        "approval_steps": ["Client review."],
    }
    response = client.post(f"/api/v1/projects/{project_id}/brief", json=brief_payload)
    assert response.status_code == 200


def test_idea_generation_selection_and_script_generation(authenticated_client, seeded_auth):
    project_id = seeded_auth["project_id"]
    _save_brief(authenticated_client, project_id)

    first_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/ideas:generate",
        headers={"Idempotency-Key": "ideas-1"},
    )
    assert first_job.status_code == 202

    second_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/ideas:generate",
        headers={"Idempotency-Key": "ideas-1"},
    )
    assert second_job.status_code == 202
    assert second_job.json()["job_id"] == first_job.json()["job_id"]

    ideas = authenticated_client.get(f"/api/v1/projects/{project_id}/ideas")
    assert ideas.status_code == 200
    assert len(ideas.json()) == 1
    assert len(ideas.json()[0]["candidates"]) == 5
    selected_idea_id = ideas.json()[0]["candidates"][0]["id"]

    select_response = authenticated_client.post(f"/api/v1/projects/{project_id}/ideas/{selected_idea_id}:select")
    assert select_response.status_code == 200

    script_job = authenticated_client.post(
        f"/api/v1/projects/{project_id}/scripts:generate",
        headers={"Idempotency-Key": "script-1"},
    )
    assert script_job.status_code == 202

    scripts = authenticated_client.get(f"/api/v1/projects/{project_id}/scripts")
    assert scripts.status_code == 200
    assert len(scripts.json()) == 1
    script_version_id = scripts.json()[0]["id"]

    patch_payload = {
        "approval_state": "draft",
        "lines": [
            {
                "id": "line_01",
                "scene_id": "scene_01",
                "beat": "Cold open",
                "narration": "This is the serum creators reach for when they want glow with proof.",
                "caption": "Clinical glow.",
                "duration_sec": 12,
                "status": "draft",
                "visual_direction": "Macro texture shot.",
                "voice_pacing": "Measured and calm",
            }
        ],
        "metadata": {},
    }
    patched = authenticated_client.patch(
        f"/api/v1/projects/{project_id}/scripts/{script_version_id}",
        json=patch_payload,
    )
    assert patched.status_code == 200
    assert patched.json()["version_number"] == 2

    detail = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    assert len(detail.json()["recent_jobs"]) >= 2
    assert detail.json()["active_script_version"]["version_number"] == 2
