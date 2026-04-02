from __future__ import annotations

import base64

import httpx

from app.core.config import Settings
from app.integrations.media import AzureOpenAIImageProvider, AzureOpenAISpeechProvider


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


def test_azure_image_provider_uses_supported_portrait_size(monkeypatch):
    captured_json: dict[str, object] = {}

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, list[dict[str, str]]]:
            return {"data": [{"b64_json": base64.b64encode(b"png-bytes").decode("ascii")}]}

    def _fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object] | None = None,
        timeout: float,
    ) -> _FakeResponse:
        del url, headers, timeout
        captured_json.update(json or {})
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", _fake_post)

    provider = AzureOpenAIImageProvider(
        Settings(environment="test"),
        endpoint="https://example.cognitiveservices.azure.com",
        api_key="test-key",
        deployment="gpt-image-1",
    )

    generated = provider.generate_frame(
        prompt="A dramatic portrait frame",
        scene_index=1,
        frame_kind="start",
        reference_images=[],
        consistency_pack_state=None,
    )

    assert captured_json["size"] == "1024x1536"
    assert generated.metadata["width"] == 1024
    assert generated.metadata["height"] == 1536


def test_azure_speech_provider_keeps_gpt_audio_on_chat_completions(monkeypatch):
    calls: list[tuple[str, dict[str, object]]] = []

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, list[dict[str, dict[str, dict[str, str]]]]]:
            return {
                "choices": [
                    {
                        "message": {
                            "audio": {
                                "data": base64.b64encode(b"wav-bytes").decode("ascii"),
                            }
                        }
                    }
                ]
            }

    def _fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object] | None = None,
        timeout: float,
    ) -> _FakeResponse:
        del headers, timeout
        calls.append((url, dict(json or {})))
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", _fake_post)

    provider = AzureOpenAISpeechProvider(
        Settings(environment="test"),
        endpoint="https://example.cognitiveservices.azure.com",
        api_key="test-key",
        deployment="gpt-audio-1.5-2",
        api_version="2025-04-01-preview",
        model="gpt-audio-1.5",
        default_voice="alloy",
    )

    generated = provider.synthesize(
        text="Narrate this exactly.",
        scene_index=1,
        voice_preset={"provider_voice": "alloy"},
    )

    assert len(calls) == 1
    assert "/chat/completions" in calls[0][0]
    assert "/audio/speech" not in calls[0][0]
    assert calls[0][1]["model"] == "gpt-audio-1.5-2"
    messages = calls[0][1]["messages"]
    assert isinstance(messages, list)
    assert messages[1]["content"][0]["text"] == "Narrate this exactly."
    assert generated.content_type == "audio/wav"


def test_azure_speech_provider_normalizes_series_voice_aliases(monkeypatch):
    calls: list[dict[str, object]] = []

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, list[dict[str, dict[str, dict[str, str]]]]]:
            return {
                "choices": [
                    {
                        "message": {
                            "audio": {
                                "data": base64.b64encode(b"wav-bytes").decode("ascii"),
                            }
                        }
                    }
                ]
            }

    def _fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object] | None = None,
        timeout: float,
    ) -> _FakeResponse:
        del url, headers, timeout
        calls.append(dict(json or {}))
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", _fake_post)

    provider = AzureOpenAISpeechProvider(
        Settings(environment="test"),
        endpoint="https://example.cognitiveservices.azure.com",
        api_key="test-key",
        deployment="gpt-audio-1.5-2",
        api_version="2025-04-01-preview",
        model="gpt-audio-1.5",
        default_voice="alloy",
    )

    provider.synthesize(
        text="Narrate this exactly.",
        scene_index=1,
        voice_preset={"provider_voice": "adam"},
    )

    assert calls[0]["audio"]["voice"] == "alloy"
