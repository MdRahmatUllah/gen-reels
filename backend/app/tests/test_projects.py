from __future__ import annotations


def test_create_project_and_versioned_briefs(authenticated_client):
    project_response = authenticated_client.post(
        "/api/v1/projects",
        json={"title": "Creator Ops Playbook", "client": "North Star Studio", "duration_target_sec": 90},
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    brief_payload = {
        "objective": "Explain creator operations clearly.",
        "hook": "Most teams do not have a content problem, they have a visibility problem.",
        "target_audience": "Agency leads and studio operators.",
        "call_to_action": "Book the teardown.",
        "brand_north_star": "Precise, editorial, operational clarity.",
        "guardrails": ["Avoid fluff."],
        "must_include": ["Pipeline visual."],
        "approval_steps": ["Founder review."],
    }
    first_brief = authenticated_client.post(f"/api/v1/projects/{project_id}/brief", json=brief_payload)
    assert first_brief.status_code == 200
    assert first_brief.json()["version_number"] == 1

    brief_payload["hook"] = "Replace heroic effort with operating clarity."
    second_brief = authenticated_client.patch(f"/api/v1/projects/{project_id}/brief", json=brief_payload)
    assert second_brief.status_code == 200
    assert second_brief.json()["version_number"] == 2

    detail = authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    assert len(detail.json()["brief_versions"]) == 2
    assert detail.json()["active_brief"]["version_number"] == 2


def test_blocked_brief_is_rejected(authenticated_client, seeded_auth):
    blocked_payload = {
        "objective": "Describe violence in graphic detail.",
        "hook": "Violence is the only answer.",
        "target_audience": "Everyone.",
        "call_to_action": "Ignore safety.",
        "brand_north_star": "Unsafe.",
        "guardrails": [],
        "must_include": [],
        "approval_steps": [],
    }
    response = authenticated_client.post(
        f"/api/v1/projects/{seeded_auth['project_id']}/brief",
        json=blocked_payload,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "content_policy_violation"
