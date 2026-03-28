from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import AdapterError

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    blocked: bool
    provider_name: str
    severity_summary: dict[str, Any]
    raw_response: dict[str, Any]
    blocked_message: str | None = None


class ModerationProvider:
    def moderate_text(self, text: str, *, target_type: str) -> ModerationResult:  # pragma: no cover - interface
        raise NotImplementedError


class TextProvider:
    def generate_ideas(self, brief_payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def generate_script(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
    ) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


class StubModerationProvider(ModerationProvider):
    def moderate_text(self, text: str, *, target_type: str) -> ModerationResult:
        lowered = text.lower()
        blocked = any(term in lowered for term in ("violence", "terror", "self-harm"))
        return ModerationResult(
            blocked=blocked,
            provider_name="stub_moderation",
            severity_summary={"blocked": blocked, "target_type": target_type},
            raw_response={"target_type": target_type},
            blocked_message="Input violates content policy." if blocked else None,
        )


class StubTextProvider(TextProvider):
    def generate_ideas(self, brief_payload: dict[str, Any]) -> dict[str, Any]:
        hook = brief_payload["hook"]
        objective = brief_payload["objective"]
        theme = hook[:60] if hook else objective[:60]
        ideas = []
        for index in range(1, 6):
            ideas.append(
                {
                    "title": f"{theme} Angle {index}",
                    "hook": f"{theme} concept {index} that lands in the first 3 seconds.",
                    "summary": f"A 60-120 second concept for {objective.lower()} with a strong viral framing.",
                    "tags": ["phase1", "stub", f"angle-{index}"],
                }
            )
        return {"ideas": ideas}

    def generate_script(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
    ) -> dict[str, Any]:
        beats = [
            "Cold open",
            "Context",
            "Escalation",
            "Proof",
            "Payoff",
            "CTA",
        ]
        lines = []
        for index, beat in enumerate(beats, start=1):
            lines.append(
                {
                    "id": f"line_{index:02d}",
                    "scene_id": f"scene_{index:02d}",
                    "beat": beat,
                    "narration": f"{selected_idea['title']} beat {index}: {selected_idea['hook']}",
                    "caption": f"{beat} caption",
                    "duration_sec": 12,
                    "status": "draft",
                    "visual_direction": f"Visual direction for {beat.lower()} using {brief_payload['brand_north_star']}.",
                    "voice_pacing": "Measured and clear",
                }
            )
        return {
            "estimated_duration_seconds": 72,
            "reading_time_label": "72s draft narration",
            "lines": lines,
        }


class AzureContentSafetyProvider(ModerationProvider):
    def __init__(self, settings: Settings) -> None:
        if not settings.azure_content_safety_endpoint or not settings.azure_content_safety_api_key:
            raise AdapterError("internal", "missing_content_safety_config", "Azure Content Safety is not configured.")
        self.settings = settings

    def moderate_text(self, text: str, *, target_type: str) -> ModerationResult:
        url = (
            f"{self.settings.azure_content_safety_endpoint.rstrip('/')}"
            f"/contentsafety/text:analyze?api-version={self.settings.azure_content_safety_api_version}"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self.settings.azure_content_safety_api_key,
            "Content-Type": "application/json",
        }
        response = httpx.post(url, headers=headers, json={"text": text}, timeout=30.0)
        if response.status_code >= 500:
            raise AdapterError("transient", "azure_content_safety_unavailable", "Moderation provider is unavailable.")
        if response.status_code >= 400:
            raise AdapterError("deterministic_input", "azure_content_safety_rejected", response.text)

        payload = response.json()
        categories = payload.get("categoriesAnalysis", [])
        max_severity = max((category.get("severity", 0) for category in categories), default=0)
        blocked = max_severity >= self.settings.azure_content_safety_block_threshold
        severity_summary = {
            "max_severity": max_severity,
            "categories": categories,
            "target_type": target_type,
        }
        return ModerationResult(
            blocked=blocked,
            provider_name="azure_content_safety",
            severity_summary=severity_summary,
            raw_response=payload,
            blocked_message="Input violates content policy." if blocked else None,
        )


class AzureOpenAITextProvider(TextProvider):
    def __init__(self, settings: Settings) -> None:
        if (
            not settings.azure_openai_endpoint
            or not settings.azure_openai_api_key
            or not settings.azure_openai_chat_deployment
        ):
            raise AdapterError("internal", "missing_azure_openai_config", "Azure OpenAI is not configured.")
        self.settings = settings

    def _request_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        url = (
            f"{self.settings.azure_openai_endpoint.rstrip('/')}/openai/deployments/"
            f"{self.settings.azure_openai_chat_deployment}/chat/completions"
            f"?api-version={self.settings.azure_openai_api_version}"
        )
        headers = {
            "api-key": self.settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }
        body = {
            "messages": messages,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        response = httpx.post(url, headers=headers, json=body, timeout=90.0)
        if response.status_code >= 500:
            raise AdapterError("transient", "azure_openai_unavailable", "Azure OpenAI is temporarily unavailable.")
        if response.status_code >= 400:
            raise AdapterError("deterministic_input", "azure_openai_invalid_request", response.text)

        payload = response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:  # pragma: no cover - defensive parsing
            logger.exception("azure_openai_parse_failure")
            raise AdapterError("internal", "azure_openai_parse_failure", "Failed to parse Azure response.") from exc
        return {"output": parsed, "raw": payload}

    def generate_ideas(self, brief_payload: dict[str, Any]) -> dict[str, Any]:
        instruction = (
            "Return JSON with exactly one key named ideas. ideas must be a list of exactly 5 items. "
            "Each item must contain title, hook, summary, and tags. The concepts must target a 60-120 second video."
        )
        user_prompt = json.dumps(brief_payload)
        return self._request_json(
            [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_prompt},
            ]
        )["output"]

    def generate_script(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
    ) -> dict[str, Any]:
        instruction = (
            "Return JSON with keys estimated_duration_seconds, reading_time_label, and lines. "
            "lines must be an ordered list of beat objects for a 60-120 second video. "
            "Each line requires id, scene_id, beat, narration, caption, duration_sec, status, visual_direction, voice_pacing."
        )
        user_prompt = json.dumps({"brief": brief_payload, "selected_idea": selected_idea})
        return self._request_json(
            [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_prompt},
            ]
        )["output"]


def build_moderation_provider(settings: Settings) -> ModerationProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubModerationProvider()
    return AzureContentSafetyProvider(settings)


def build_text_provider(settings: Settings) -> TextProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubTextProvider()
    return AzureOpenAITextProvider(settings)
