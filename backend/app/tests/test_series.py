from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AdapterError
from app.db.session import get_session_factory
from app.integrations.azure import StubTextProvider
from app.models.entities import (
    Asset,
    AssetRole,
    AssetType,
    ExecutionMode,
    ExportRecord,
    JobKind,
    JobStatus,
    RenderJob,
    RenderStep,
    ScriptSource,
    ScriptVersion,
    Series,
    SeriesRun,
    SeriesScript,
    SeriesScriptRevision,
    SeriesVideoRun,
    SeriesVideoRunStep,
    StepKind,
)
from app.services.content_planning_service import ContentPlanningService
from app.services.render_service import RenderService
from app.services.series_video_service import SeriesVideoService
from app.services.routing_service import RoutingDecision


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


def _list_scripts(authenticated_client, series_id: str) -> list[dict[str, object]]:
    response = authenticated_client.get(f"/api/v1/series/{series_id}/scripts")
    assert response.status_code == 200
    return response.json()


def _get_script_detail(authenticated_client, series_id: str, script_id: str) -> dict[str, object]:
    response = authenticated_client.get(f"/api/v1/series/{series_id}/scripts/{script_id}")
    assert response.status_code == 200
    return response.json()


def _approve_script(authenticated_client, series_id: str, script_id: str) -> dict[str, object]:
    response = authenticated_client.post(f"/api/v1/series/{series_id}/scripts/{script_id}:approve")
    assert response.status_code == 200
    return response.json()


def _reject_script(authenticated_client, series_id: str, script_id: str) -> dict[str, object]:
    response = authenticated_client.post(f"/api/v1/series/{series_id}/scripts/{script_id}:reject")
    assert response.status_code == 200
    return response.json()


def _regenerate_script(authenticated_client, series_id: str, script_id: str, key: str) -> dict[str, object]:
    response = authenticated_client.post(
        f"/api/v1/series/{series_id}/scripts/{script_id}:regenerate",
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 202
    return response.json()


def _start_video_run(
    authenticated_client,
    series_id: str,
    series_script_ids: list[str],
    key: str,
):
    return authenticated_client.post(
        f"/api/v1/series/{series_id}/video-runs",
        json={"series_script_ids": series_script_ids},
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
    assert created["primary_cta"] == "start_series"
    invalid = authenticated_client.post(
        "/api/v1/series",
        json={**_custom_series_payload(), "custom_topic": "", "title": "Broken custom"},
    )
    assert invalid.status_code == 422


def test_create_series_and_start_run_generates_reviewable_scripts_sequentially(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())
    run_response = _start_run(authenticated_client, series["id"], 3, "series-run-1")
    assert run_response.status_code == 202
    run_payload = run_response.json()
    assert run_payload["status"] == "completed"
    assert [step["status"] for step in run_payload["steps"]] == ["completed", "completed", "completed"]
    assert [step["sequence_number"] for step in run_payload["steps"]] == [1, 2, 3]

    detail_response = authenticated_client.get(f"/api/v1/series/{series['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["total_script_count"] == 3
    assert detail["scripts_awaiting_review_count"] == 3
    assert detail["approved_script_count"] == 0
    assert detail["primary_cta"] == "create_video"

    scripts = _list_scripts(authenticated_client, series["id"])
    assert [script["sequence_number"] for script in scripts] == [1, 2, 3]
    assert all(script["title"] for script in scripts)
    assert all(script["total_words"] > 0 for script in scripts)
    assert all(script["approval_state"] == "needs_review" for script in scripts)
    assert all(script["current_revision"]["revision_number"] == 1 for script in scripts)
    assert all(script["can_approve"] is True for script in scripts)
    assert all(script["published_video"] is None for script in scripts)


def test_second_series_run_appends_sequence_numbers(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())

    first = _start_run(authenticated_client, series["id"], 2, "append-a")
    second = _start_run(authenticated_client, series["id"], 2, "append-b")
    assert first.status_code == 202
    assert second.status_code == 202
    assert [step["sequence_number"] for step in second.json()["steps"]] == [3, 4]

    scripts = _list_scripts(authenticated_client, series["id"])
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


def test_series_edit_blocked_while_active_script_run(authenticated_client, seeded_auth):
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


def test_series_edit_blocked_while_active_video_run(authenticated_client, seeded_auth):
    series = _create_series(authenticated_client, _preset_series_payload())
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        session.add(
            SeriesVideoRun(
                series_id=UUID(series["id"]),
                workspace_id=UUID(seeded_auth["workspace_id"]),
                created_by_user_id=UUID(seeded_auth["user_id"]),
                status=JobStatus.running,
                requested_video_count=1,
                idempotency_key="locked-video-run",
                request_hash="locked-video-run",
                payload={},
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

    scripts = _list_scripts(authenticated_client, series["id"])
    assert len(scripts) == 1
    assert scripts[0]["sequence_number"] == 1


def test_series_script_review_regeneration_and_detail_routes(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())
    _start_run(authenticated_client, series["id"], 1, "review-flow")

    scripts = _list_scripts(authenticated_client, series["id"])
    script_id = scripts[0]["id"]

    rejected = _reject_script(authenticated_client, series["id"], script_id)
    assert rejected["approval_state"] == "rejected"
    assert rejected["approved_revision"] is None
    assert rejected["can_create_video"] is False

    approved = _approve_script(authenticated_client, series["id"], script_id)
    assert approved["approval_state"] == "approved"
    assert approved["approved_revision"]["revision_number"] == 1
    assert approved["can_create_video"] is True

    regenerated_run = _regenerate_script(authenticated_client, series["id"], script_id, "regen-1")
    assert regenerated_run["status"] == "completed"
    assert regenerated_run["steps"][0]["series_script_id"] == script_id

    detail = _get_script_detail(authenticated_client, series["id"], script_id)
    assert detail["script"]["sequence_number"] == 1
    assert detail["script"]["approval_state"] == "needs_review"
    assert detail["script"]["current_revision"]["revision_number"] == 2
    assert detail["script"]["approved_revision"]["revision_number"] == 1
    assert len(detail["revisions"]) == 2
    assert detail["scenes"] == []


def test_series_video_run_uses_approved_scripts_only_and_hides_internal_projects(authenticated_client):
    series = _create_series(authenticated_client, _preset_series_payload())
    _start_run(authenticated_client, series["id"], 2, "video-flow")

    scripts = _list_scripts(authenticated_client, series["id"])
    first_script_id = scripts[0]["id"]
    second_script_id = scripts[1]["id"]
    _approve_script(authenticated_client, series["id"], first_script_id)

    video_response = _start_video_run(
        authenticated_client,
        series["id"],
        [first_script_id, second_script_id],
        "video-run-1",
    )
    assert video_response.status_code == 202
    run_payload = video_response.json()
    assert run_payload["status"] == "completed"
    assert run_payload["requested_video_count"] == 1
    assert run_payload["completed_video_count"] == 1
    assert len(run_payload["steps"]) == 1
    hidden_project_id = run_payload["steps"][0]["hidden_project_id"]
    assert hidden_project_id
    assert run_payload["steps"][0]["render_job_id"]

    replay = _start_video_run(
        authenticated_client,
        series["id"],
        [first_script_id, second_script_id],
        "video-run-1",
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == run_payload["id"]

    updated_scripts = _list_scripts(authenticated_client, series["id"])
    published = next(script for script in updated_scripts if script["id"] == first_script_id)
    untouched = next(script for script in updated_scripts if script["id"] == second_script_id)
    assert published["video_status"] == "completed"
    assert published["video_phase"] == "completed"
    assert published["published_video"] is not None
    assert published["published_video"]["download_url"]
    assert published["published_revision"]["video_title"]
    assert "#" in published["published_revision"]["video_description"]
    assert untouched["published_video"] is None

    detail = _get_script_detail(authenticated_client, series["id"], first_script_id)
    assert detail["latest_render_status"] == "completed"
    assert detail["latest_render_job_id"] is not None
    assert detail["scenes"]
    assert any(scene["narration_asset"] is not None for scene in detail["scenes"])

    series_detail = authenticated_client.get(f"/api/v1/series/{series['id']}")
    assert series_detail.status_code == 200
    assert series_detail.json()["completed_video_count"] == 1

    projects = authenticated_client.get("/api/v1/projects")
    assert projects.status_code == 200
    assert all(project["id"] != hidden_project_id for project in projects.json())

    hidden_detail = authenticated_client.get(f"/api/v1/projects/{hidden_project_id}")
    assert hidden_detail.status_code == 404


def test_series_video_run_falls_back_to_stub_narration_when_speech_provider_rejects(
    authenticated_client,
    monkeypatch,
):
    class RejectingSpeechProvider:
        def synthesize(self, *, text: str, scene_index: int, voice_preset):
            del text, scene_index, voice_preset
            raise AdapterError(
                "configuration",
                "azure_speech_rejected",
                "Speech provider rejected the request.",
            )

    def fake_speech_provider(self, step, workspace_id):
        del self, step, workspace_id
        return (
            RejectingSpeechProvider(),
            RoutingDecision(
                modality="speech",
                execution_mode=ExecutionMode.hosted,
                provider_key="azure_openai_speech",
                provider_name="azure_openai_speech",
                provider_model="gpt-audio-1.5",
                reason="test_override",
            ),
        )

    monkeypatch.setattr(RenderService, "_speech_provider_and_decision", fake_speech_provider)

    series = _create_series(authenticated_client, _preset_series_payload())
    _start_run(authenticated_client, series["id"], 1, "video-fallback-script")

    script_id = _list_scripts(authenticated_client, series["id"])[0]["id"]
    _approve_script(authenticated_client, series["id"], script_id)

    video_response = _start_video_run(
        authenticated_client,
        series["id"],
        [script_id],
        "video-fallback-run",
    )
    assert video_response.status_code == 202
    run_payload = video_response.json()
    assert run_payload["status"] == "completed"
    assert run_payload["completed_video_count"] == 1

    detail = _get_script_detail(authenticated_client, series["id"], script_id)
    assert detail["latest_render_status"] == "completed"
    assert detail["scenes"]
    assert all(scene["narration_asset"] is not None for scene in detail["scenes"])

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        narration_asset = session.scalar(
            select(Asset)
            .where(
                Asset.render_job_id == UUID(str(detail["latest_render_job_id"])),
                Asset.asset_role == AssetRole.narration_track,
            )
            .order_by(Asset.created_at.desc())
        )
        assert narration_asset is not None
        assert narration_asset.metadata_payload["fallback_mode"] == "stub_speech_due_to_provider_error"
        assert narration_asset.metadata_payload["fallback_error_code"] == "azure_speech_rejected"
    finally:
        session.close()


def test_get_series_video_run_recovers_orphaned_render_step(
    authenticated_client,
    seeded_auth,
    monkeypatch,
):
    queued_resumes: list[str] = []

    def fake_queue_render_resume(self, render_job_id):
        del self
        queued_resumes.append(str(render_job_id))

    monkeypatch.setattr(RenderService, "_queue_render_resume", fake_queue_render_resume)

    series = _create_series(authenticated_client, _preset_series_payload())
    _start_run(authenticated_client, series["id"], 1, "series-orphan-recovery-script")
    script = _list_scripts(authenticated_client, series["id"])[0]
    script_detail = _get_script_detail(authenticated_client, series["id"], script["id"])

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        stale_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        video_run = SeriesVideoRun(
            series_id=UUID(series["id"]),
            workspace_id=UUID(seeded_auth["workspace_id"]),
            created_by_user_id=UUID(seeded_auth["user_id"]),
            status=JobStatus.running,
            requested_video_count=1,
            completed_video_count=0,
            failed_video_count=0,
            idempotency_key="series-orphan-recovery-run",
            request_hash="series-orphan-recovery-run",
            payload={},
            started_at=stale_at,
        )
        session.add(video_run)
        session.flush()

        render_job = RenderJob(
            workspace_id=UUID(seeded_auth["workspace_id"]),
            project_id=UUID(seeded_auth["project_id"]),
            created_by_user_id=UUID(seeded_auth["user_id"]),
            job_kind=JobKind.render_generation,
            queue_name="render",
            status=JobStatus.review,
            idempotency_key="series-orphan-render",
            request_hash="series-orphan-render",
            payload={},
            allow_export_without_music=True,
            started_at=stale_at,
        )
        session.add(render_job)
        session.flush()

        render_step = RenderStep(
            render_job_id=render_job.id,
            project_id=render_job.project_id,
            step_kind=StepKind.frame_pair_generation,
            step_index=104,
            status=JobStatus.running,
            input_payload={"scene_index": 4},
            started_at=stale_at,
            last_checkpoint_at=stale_at,
        )
        session.add(render_step)
        session.flush()

        session.add(
            SeriesVideoRunStep(
                series_video_run_id=video_run.id,
                series_id=UUID(series["id"]),
                series_script_id=UUID(script["id"]),
                series_script_revision_id=UUID(str(script_detail["script"]["current_revision"]["id"])),
                step_index=1,
                sequence_number=1,
                status=JobStatus.running,
                phase="generating_frames",
                render_job_id=render_job.id,
                current_scene_index=4,
                current_scene_count=8,
                started_at=stale_at,
            )
        )
        session.commit()

        response = authenticated_client.get(f"/api/v1/series/{series['id']}/video-runs/{video_run.id}")
        assert response.status_code == 200

        session.expire_all()
        recovered_job = session.get(RenderJob, render_job.id)
        recovered_step = session.get(RenderStep, render_step.id)
        assert recovered_job is not None
        assert recovered_step is not None
        assert recovered_job.status == JobStatus.queued
        assert recovered_step.status == JobStatus.queued
        assert recovered_step.checkpoint_payload["reason"] == "orphaned_render_recovery"
        assert queued_resumes == [str(render_job.id)]
    finally:
        session.close()


def test_execute_video_run_reuses_existing_render_job_on_resume(
    authenticated_client,
    seeded_auth,
    monkeypatch,
):
    def _unexpected_queue(*args, **kwargs):
        raise AssertionError("resume should reuse existing internal jobs instead of queueing new ones")

    monkeypatch.setattr(ContentPlanningService, "queue_scene_plan_generation", _unexpected_queue)
    monkeypatch.setattr(ContentPlanningService, "queue_prompt_pair_generation", _unexpected_queue)
    monkeypatch.setattr(RenderService, "queue_render_job", _unexpected_queue)

    series = _create_series(authenticated_client, _preset_series_payload())
    run_response = _start_run(authenticated_client, series["id"], 1, "series-resume-existing-render-script")
    assert run_response.status_code == 202
    script = _list_scripts(authenticated_client, series["id"])[0]
    _approve_script(authenticated_client, series["id"], script["id"])
    script_detail = _get_script_detail(authenticated_client, series["id"], script["id"])

    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        service = SeriesVideoService(session, settings)
        series_record = session.get(Series, UUID(series["id"]))
        script_record = session.get(SeriesScript, UUID(script["id"]))
        revision = session.get(SeriesScriptRevision, UUID(str(script_detail["script"]["current_revision"]["id"])))
        assert series_record is not None
        assert script_record is not None
        assert revision is not None

        project = service._ensure_hidden_project(series_record, script_record, UUID(seeded_auth["user_id"]))
        service._sync_hidden_project(
            series=series_record,
            slot=script_record,
            revision=revision,
            project=project,
            user_id=UUID(seeded_auth["user_id"]),
        )
        session.refresh(project)
        original_script = session.get(ScriptVersion, project.active_script_version_id)
        assert original_script is not None

        stale_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        video_run = SeriesVideoRun(
            series_id=UUID(series["id"]),
            workspace_id=UUID(seeded_auth["workspace_id"]),
            created_by_user_id=UUID(seeded_auth["user_id"]),
            status=JobStatus.failed,
            requested_video_count=1,
            completed_video_count=0,
            failed_video_count=1,
            idempotency_key="series-resume-existing-render-run",
            request_hash="series-resume-existing-render-run",
            payload={},
            started_at=stale_at,
            completed_at=stale_at,
        )
        session.add(video_run)
        session.flush()

        step = SeriesVideoRunStep(
            series_video_run_id=video_run.id,
            series_id=UUID(series["id"]),
            series_script_id=script_record.id,
            series_script_revision_id=revision.id,
            step_index=1,
            sequence_number=1,
            status=JobStatus.failed,
            phase="generating_scenes",
            hidden_project_id=project.id,
            current_scene_index=4,
            current_scene_count=8,
            error_code="unexpected_error",
            error_message="This Idempotency-Key was already used for a different request.",
            started_at=stale_at,
            completed_at=stale_at,
        )
        session.add(step)
        session.flush()

        scene_request_payload = {
            "project_id": str(project.id),
            "script_version_id": str(original_script.id),
            "script_version_number": original_script.version_number,
            "visual_preset_id": str(project.default_visual_preset_id),
            "voice_preset_id": str(project.default_voice_preset_id),
        }
        session.add(
            RenderJob(
                workspace_id=project.workspace_id,
                project_id=project.id,
                created_by_user_id=UUID(seeded_auth["user_id"]),
                job_kind=JobKind.scene_plan_generation,
                status=JobStatus.completed,
                idempotency_key=f"series-video-scene-{step.id}",
                request_hash=service._hash_request(scene_request_payload),
                payload=scene_request_payload,
                started_at=stale_at,
                completed_at=stale_at,
            )
        )

        render_job = RenderJob(
            workspace_id=project.workspace_id,
            project_id=project.id,
            created_by_user_id=UUID(seeded_auth["user_id"]),
            script_version_id=original_script.id,
            job_kind=JobKind.render_generation,
            queue_name="render",
            status=JobStatus.completed,
            idempotency_key=f"series-video-render-{step.id}",
            request_hash="series-resume-existing-render-hash",
            payload={},
            allow_export_without_music=True,
            started_at=stale_at,
            completed_at=stale_at,
        )
        session.add(render_job)
        session.flush()
        step.render_job_id = render_job.id

        asset = Asset(
            workspace_id=project.workspace_id,
            project_id=project.id,
            render_job_id=render_job.id,
            asset_type=AssetType.export,
            asset_role=AssetRole.final_export,
            status="completed",
            bucket_name="tests",
            object_name=f"exports/{render_job.id}.mp4",
            file_name="resume-test.mp4",
            content_type="video/mp4",
            size_bytes=1024,
            duration_ms=61000,
            has_audio_stream=True,
        )
        session.add(asset)
        session.flush()
        session.add(
            ExportRecord(
                workspace_id=project.workspace_id,
                project_id=project.id,
                render_job_id=render_job.id,
                asset_id=asset.id,
                status="completed",
                file_name="resume-test.mp4",
                format="mp4",
                bucket_name="tests",
                object_name=f"exports/final-{render_job.id}.mp4",
                subtitle_style_profile={},
                export_profile={},
                audio_mix_profile={},
                metadata_payload={},
                completed_at=stale_at,
            )
        )

        resumed_script = ScriptVersion(
            project_id=project.id,
            based_on_idea_id=project.selected_idea_id,
            created_by_user_id=UUID(seeded_auth["user_id"]),
            version_number=original_script.version_number + 1,
            version=1,
            source_type=ScriptSource.generated,
            approval_state="approved",
            total_words=original_script.total_words,
            estimated_duration_seconds=original_script.estimated_duration_seconds,
            reading_time_label=original_script.reading_time_label,
            lines=list(original_script.lines or []),
        )
        session.add(resumed_script)
        session.flush()
        project.active_script_version_id = resumed_script.id
        session.commit()

        service.execute_video_run(str(video_run.id))

        session.expire_all()
        refreshed_run = session.get(SeriesVideoRun, video_run.id)
        refreshed_step = session.get(SeriesVideoRunStep, step.id)
        refreshed_slot = session.get(SeriesScript, script_record.id)
        refreshed_project = session.get(type(project), project.id)
        assert refreshed_run is not None
        assert refreshed_step is not None
        assert refreshed_slot is not None
        assert refreshed_project is not None
        assert refreshed_run.status == JobStatus.completed
        assert refreshed_run.completed_video_count == 1
        assert refreshed_run.failed_video_count == 0
        assert refreshed_run.error_message is None
        assert refreshed_step.status == JobStatus.completed
        assert refreshed_step.render_job_id == render_job.id
        assert refreshed_project.active_script_version_id == original_script.id
        assert refreshed_slot.published_render_job_id == render_job.id
        assert refreshed_slot.published_export_id is not None
    finally:
        session.close()
