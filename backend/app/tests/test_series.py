from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.integrations.azure import StubTextProvider
from app.models.entities import JobStatus, SeriesRun


def _preset_series_payload() -> dict[str, object]:
    return {
        "title": "Midnight Myths",
        "description": "Short scary stories for viral reels.",
        "content_mode": "preset",
        "preset_key": "scary_stories",
        "custom_topic": "",
        "custom_example_script": "",
        "language_key": "en",
        "voice_key": "adam",
        "music_mode": "preset",
        "music_keys": ["breathing_shadows", "deep_bass"],
        "art_style_key": "dark_fantasy",
        "caption_style_key": "bold_stroke",
        "effect_keys": ["shake_effect", "film_grain"],
    }


def _custom_series_payload() -> dict[str, object]:
    return {
        "title": "History Is Weird",
        "description": "One-minute history stories with humor.",
        "content_mode": "custom",
        "preset_key": None,
        "custom_topic": "Weird historical facts that sound fake but are real, told conversationally with humor.",
        "custom_example_script": (
            "Okay so get this, in 1932 Australia literally fought emus and lost. "
            "History is absurd sometimes."
        ),
        "language_key": "en",
        "voice_key": "john",
        "music_mode": "none",
        "music_keys": [],
        "art_style_key": "comic",
        "caption_style_key": "sleek",
        "effect_keys": [],
    }


def _create_series(authenticated_client, payload: dict[str, object]) -> dict[str, object]:
    response = authenticated_client.post("/api/v1/series", json=payload)
    assert response.status_code == 201
    return response.json()


def _start_run(authenticated_client, series_id: str, count: int, key: str):
    return authenticated_client.post(
        f"/api/v1/series/{series_id}/runs",
        json={"requested_script_count": count},
        headers={"Idempotency-Key": key},
    )


def test_series_catalog_contract(authenticated_client):
    response = authenticated_client.get("/api/v1/series/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert [item["key"] for item in payload["content_presets"]] == [
        "scary_stories",
        "historical_figures",
        "greek_mythology",
        "important_events",
        "true_crime",
        "stoic_motivation",
        "good_morals",
    ]
    assert [item["key"] for item in payload["voices"]] == [
        "adam",
        "john",
        "confident_narrator",
        "warm_storyteller",
        "ava_editorial",
        "energetic_host",
    ]
    assert [item["key"] for item in payload["music"]] == [
        "happy_rhythm",
        "quiet_before_storm",
        "brilliant_symphony",
        "breathing_shadows",
        "eight_bit_slowed",
        "deep_bass",
    ]
    assert [item["key"] for item in payload["languages"]] == ["en"]


def test_create_custom_series_and_validation(authenticated_client):
    created = _create_series(authenticated_client, _custom_series_payload())
    assert created["content_mode"] == "custom"
    assert created["custom_example_script"]
    invalid = authenticated_client.post(
        "/api/v1/series",
        json={**_custom_series_payload(), "custom_topic": "", "title": "Broken custom"},
    )
    assert invalid.status_code == 422


def test_create_series_and_start_run_generates_scripts_sequentially(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())
    run_response = _start_run(authenticated_client, series["id"], 3, "series-run-1")
    assert run_response.status_code == 202
    run_payload = run_response.json()
    assert run_payload["status"] == "completed"
    assert [step["status"] for step in run_payload["steps"]] == ["completed", "completed", "completed"]
    assert [step["sequence_number"] for step in run_payload["steps"]] == [1, 2, 3]

    scripts_response = authenticated_client.get(f"/api/v1/series/{series['id']}/scripts")
    assert scripts_response.status_code == 200
    scripts = scripts_response.json()
    assert [script["sequence_number"] for script in scripts] == [1, 2, 3]
    assert all(script["title"] for script in scripts)
    assert all(script["total_words"] > 0 for script in scripts)


def test_second_series_run_appends_sequence_numbers(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())

    first = _start_run(authenticated_client, series["id"], 2, "append-a")
    second = _start_run(authenticated_client, series["id"], 2, "append-b")
    assert first.status_code == 202
    assert second.status_code == 202
    assert [step["sequence_number"] for step in second.json()["steps"]] == [3, 4]

    scripts = authenticated_client.get(f"/api/v1/series/{series['id']}/scripts").json()
    assert [script["sequence_number"] for script in scripts] == [1, 2, 3, 4]


def test_series_run_idempotency_replays_same_run(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())

    first = _start_run(authenticated_client, series["id"], 2, "same-key")
    second = _start_run(authenticated_client, series["id"], 2, "same-key")
    conflict = _start_run(authenticated_client, series["id"], 3, "same-key")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_series_edit_blocked_while_active_run(authenticated_client, seeded_auth):
    series = _create_series(authenticated_client, _preset_series_payload())
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        session.add(
            SeriesRun(
                series_id=UUID(series["id"]),
                workspace_id=UUID(seeded_auth["workspace_id"]),
                created_by_user_id=UUID(seeded_auth["user_id"]),
                status=JobStatus.queued,
                requested_script_count=3,
                idempotency_key="locked-run",
                request_hash="lock-hash",
                payload={"series_snapshot": {"title": series["title"]}},
            )
        )
        session.commit()
    finally:
        session.close()

    response = authenticated_client.patch(
        f"/api/v1/series/{series['id']}",
        json={**_preset_series_payload(), "title": "Edited title"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "series_locked"


def test_series_run_passes_prior_context_to_provider(authenticated_client, monkeypatch):
    captured_prior: list[dict[str, object]] = []

    def fake_generate_series_script(self, *, series_payload, sequence_number, prior_scripts):
        captured_prior.append(
            {
                "sequence_number": sequence_number,
                "prior_scripts": prior_scripts,
                "series_title": series_payload["title"],
            }
        )
        return {
            "title": f"Episode {sequence_number}",
            "summary": f"Summary {sequence_number}",
            "estimated_duration_seconds": 60,
            "reading_time_label": "60s draft narration",
            "lines": [
                {
                    "id": "line_01",
                    "scene_id": "scene_01",
                    "beat": "Hook",
                    "narration": f"Episode {sequence_number} narration",
                    "caption": "Hook caption",
                    "duration_sec": 60,
                    "status": "draft",
                    "visual_direction": "Cinematic close-up",
                    "voice_pacing": "Measured",
                }
            ],
        }

    monkeypatch.setattr(StubTextProvider, "generate_series_script", fake_generate_series_script)
    series = _create_series(authenticated_client, _preset_series_payload())

    response = _start_run(authenticated_client, series["id"], 2, "capture-prior")
    assert response.status_code == 202
    assert captured_prior[0]["prior_scripts"] == []
    assert captured_prior[1]["series_title"] == "Midnight Myths"
    assert [item["title"] for item in captured_prior[1]["prior_scripts"]] == ["Episode 1"]
    assert captured_prior[1]["prior_scripts"][0]["summary"] == "Summary 1"


def test_series_run_failure_marks_current_step_and_keeps_prior_scripts(authenticated_client, monkeypatch):
    call_count = {"value": 0}

    def flaky_generate_series_script(self, *, series_payload, sequence_number, prior_scripts):
        del self, series_payload, prior_scripts
        call_count["value"] += 1
        if call_count["value"] == 2:
            raise AdapterError("deterministic_input", "series_provider_failed", "Provider exploded.")
        return {
            "title": f"Episode {sequence_number}",
            "summary": f"Summary {sequence_number}",
            "estimated_duration_seconds": 60,
            "reading_time_label": "60s draft narration",
            "lines": [
                {
                    "id": "line_01",
                    "scene_id": "scene_01",
                    "beat": "Hook",
                    "narration": f"Episode {sequence_number} narration",
                    "caption": "Hook caption",
                    "duration_sec": 60,
                    "status": "draft",
                    "visual_direction": "Cinematic close-up",
                    "voice_pacing": "Measured",
                }
            ],
        }

    monkeypatch.setattr(StubTextProvider, "generate_series_script", flaky_generate_series_script)
    series = _create_series(authenticated_client, _preset_series_payload())

    response = _start_run(authenticated_client, series["id"], 3, "will-fail")
    assert response.status_code == 202
    run_payload = response.json()
    assert run_payload["status"] == "failed"
    assert [step["status"] for step in run_payload["steps"]] == ["completed", "failed", "queued"]
    assert run_payload["error_code"] == "series_provider_failed"

    scripts = authenticated_client.get(f"/api/v1/series/{series['id']}/scripts").json()
    assert len(scripts) == 1
    assert scripts[0]["sequence_number"] == 1
