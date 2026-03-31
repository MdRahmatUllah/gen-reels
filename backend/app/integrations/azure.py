from __future__ import annotations

import json
import logging
import re
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
    def synthesize_brief(
        self,
        *,
        idea_prompt: str,
        starter_context: dict[str, Any] | None,
    ) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def generate_ideas(self, brief_payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def generate_script(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
    ) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def generate_scene_plan(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
        script_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
        voice_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def generate_prompt_pairs(
        self,
        *,
        scene_plan_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


def _distribute_duration(total_duration: int, parts: int) -> list[int]:
    base = max(1, total_duration // parts)
    remainder = total_duration % parts
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def _split_narration(narration: str, parts: int) -> list[str]:
    words = narration.split()
    if not words:
        return [narration.strip()] * parts
    chunk_size = max(1, (len(words) + parts - 1) // parts)
    chunks = [
        " ".join(words[index : index + chunk_size]).strip()
        for index in range(0, len(words), chunk_size)
    ]
    while len(chunks) < parts:
        chunks.append(chunks[-1] if chunks else narration.strip())
    return chunks[:parts]


def _scene_prompt_strings(
    *,
    scene_title: str,
    beat: str,
    narration_text: str,
    visual_direction: str,
    visual_preset: dict[str, Any] | None,
) -> dict[str, str]:
    prefix = str((visual_preset or {}).get("prompt_prefix") or "").strip()
    style = str((visual_preset or {}).get("style_descriptor") or "").strip()
    camera = str((visual_preset or {}).get("camera_defaults") or "").strip()
    palette = str((visual_preset or {}).get("color_palette") or "").strip()
    visual_prompt = " ".join(
        part
        for part in [
            prefix,
            f"{scene_title} {beat}".strip(),
            visual_direction.strip(),
            camera,
            palette,
            style,
        ]
        if part
    ).strip()
    start_image_prompt = " ".join(
        part
        for part in [
            "Opening frame.",
            scene_title,
            narration_text,
            visual_direction,
            camera,
            style,
        ]
        if part
    ).strip()
    end_image_prompt = " ".join(
        part
        for part in [
            "Closing frame with visible progression from the opening frame.",
            scene_title,
            narration_text,
            visual_direction,
            palette,
            style,
        ]
        if part
    ).strip()
    return {
        "visual_prompt": visual_prompt,
        "start_image_prompt": start_image_prompt,
        "end_image_prompt": end_image_prompt,
    }


def _build_stub_scene_plan(
    *,
    selected_idea: dict[str, Any],
    script_payload: dict[str, Any],
    visual_preset: dict[str, Any] | None,
) -> dict[str, Any]:
    shot_types = ["macro", "wide", "medium", "overhead", "close-up"]
    motions = ["slow push-in", "locked", "drift", "parallax", "handheld energy"]
    scenes: list[dict[str, Any]] = []
    lines = script_payload.get("lines") or []
    scene_index = 1
    for line in lines:
        total_duration = max(1, int(line.get("duration_sec") or 6))
        parts = max(1, (total_duration + 7) // 8)
        durations = _distribute_duration(total_duration, parts)
        narrations = _split_narration(str(line.get("narration") or ""), parts)
        for part_index, part_duration in enumerate(durations, start=1):
            scene_title = f"{selected_idea['title']} Scene {scene_index}"
            beat = str(line.get("beat") or f"Beat {scene_index}")
            narration_text = narrations[part_index - 1]
            visual_direction = str(line.get("visual_direction") or "").strip()
            prompts = _scene_prompt_strings(
                scene_title=scene_title,
                beat=beat,
                narration_text=narration_text,
                visual_direction=visual_direction,
                visual_preset=visual_preset,
            )
            scenes.append(
                {
                    "scene_index": scene_index,
                    "source_line_ids": [str(line.get("id") or f"line_{scene_index:02d}")],
                    "title": scene_title,
                    "beat": beat,
                    "narration_text": narration_text,
                    "caption_text": str(line.get("caption") or ""),
                    "visual_direction": visual_direction,
                    "shot_type": shot_types[(scene_index - 1) % len(shot_types)],
                    "motion": motions[(scene_index - 1) % len(motions)],
                    "target_duration_seconds": part_duration,
                    "estimated_voice_duration_seconds": part_duration,
                    "visual_prompt": prompts["visual_prompt"],
                    "start_image_prompt": prompts["start_image_prompt"],
                    "end_image_prompt": prompts["end_image_prompt"],
                    "transition_mode": "hard_cut",
                    "notes": [],
                    "validation_warnings": [],
                }
            )
            scene_index += 1
    total_duration = sum(int(scene["target_duration_seconds"]) for scene in scenes)
    warnings: list[dict[str, Any]] = []
    if total_duration < 60 or total_duration > 120:
        warnings.append(
            {
                "code": "total_duration_out_of_range",
                "message": "Estimated total duration is outside the recommended 60-120 second range.",
            }
        )
    return {
        "scene_count": len(scenes),
        "estimated_duration_seconds": total_duration,
        "validation_warnings": warnings,
        "scenes": scenes,
    }


def _stub_project_title(idea_prompt: str) -> str:
    cleaned = " ".join(idea_prompt.strip().split())
    if not cleaned:
        return "Untitled Project"
    words = cleaned.split()
    return " ".join(words[:8]).title()[:80]


# When Content Safety is not configured, dev uses this stub. Avoid naive substrings like "violence"
# or "terror" (they match normal news/educational copy). Tests use the sentinel or fixed phrases below.
STUB_MODERATION_BLOCK_SENTINEL = "[[stub_moderation_block]]"


def _stub_moderation_should_block(text: str) -> bool:
    lowered = text.lower()
    if STUB_MODERATION_BLOCK_SENTINEL in lowered:
        return True
    if "describe violence in graphic detail" in lowered:
        return True
    if "violence is the only answer" in lowered:
        return True
    if re.search(r"\bself[- ]harm\b", lowered):
        return True
    return False


class StubModerationProvider(ModerationProvider):
    def moderate_text(self, text: str, *, target_type: str) -> ModerationResult:
        blocked = _stub_moderation_should_block(text)
        return ModerationResult(
            blocked=blocked,
            provider_name="stub_moderation",
            severity_summary={"blocked": blocked, "target_type": target_type},
            raw_response={"target_type": target_type},
            blocked_message="Input violates content policy." if blocked else None,
        )


class StubTextProvider(TextProvider):
    def synthesize_brief(
        self,
        *,
        idea_prompt: str,
        starter_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        starter_name = str((starter_context or {}).get("starter_name") or "Studio Default")
        tone = str((starter_context or {}).get("starter_description") or "creator-first short-form production")
        subject = " ".join(idea_prompt.strip().split()) or "a short-form concept"
        title = _stub_project_title(subject)
        return {
            "title": title,
            "brief": {
                "objective": f"Create a polished short-form video about {subject}.",
                "hook": f"Open with a striking first beat that makes viewers stop for {title}.",
                "target_audience": "Social-first viewers who respond to clear benefits, pace, and visual clarity.",
                "call_to_action": "Invite the viewer to take the next clear step immediately after the payoff.",
                "brand_north_star": f"{starter_name} tone with {tone}.",
                "guardrails": [
                    "Keep the narration concise and scroll-stopping.",
                    "Avoid unsupported claims and distracting side plots.",
                ],
                "must_include": [
                    "A concrete payoff within the first few beats.",
                    "A visually specific direction for the core idea.",
                ],
                "approval_steps": [
                    "Script review",
                    "Visual sign-off",
                    "Final export approval",
                ],
            },
        }

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

    def generate_scene_plan(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
        script_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
        voice_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        del brief_payload, voice_preset
        return _build_stub_scene_plan(
            selected_idea=selected_idea,
            script_payload=script_payload,
            visual_preset=visual_preset,
        )

    def generate_prompt_pairs(
        self,
        *,
        scene_plan_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        regenerated_segments = []
        for segment in scene_plan_payload.get("segments") or []:
            prompts = _scene_prompt_strings(
                scene_title=str(segment.get("title") or f"Scene {segment.get('scene_index') or ''}").strip(),
                beat=str(segment.get("beat") or "").strip(),
                narration_text=str(segment.get("narration_text") or "").strip(),
                visual_direction=str(segment.get("visual_direction") or "").strip(),
                visual_preset=visual_preset,
            )
            regenerated_segments.append(
                {
                    "scene_index": int(segment["scene_index"]),
                    "visual_prompt": prompts["visual_prompt"],
                    "start_image_prompt": prompts["start_image_prompt"],
                    "end_image_prompt": prompts["end_image_prompt"],
                    "validation_warnings": list(segment.get("validation_warnings") or []),
                }
            )
        return {"segments": regenerated_segments}


class AzureContentSafetyProvider(ModerationProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self.endpoint = endpoint or settings.azure_content_safety_endpoint
        self.api_key = api_key or settings.azure_content_safety_api_key
        self.api_version = api_version or settings.azure_content_safety_api_version
        if not self.endpoint or not self.api_key:
            raise AdapterError("internal", "missing_content_safety_config", "Azure Content Safety is not configured.")
        self.settings = settings

    def moderate_text(self, text: str, *, target_type: str) -> ModerationResult:
        url = (
            f"{self.endpoint.rstrip('/')}"
            f"/contentsafety/text:analyze?api-version={self.api_version}"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
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
    def __init__(
        self,
        settings: Settings,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self.endpoint = endpoint or settings.azure_openai_endpoint
        self.api_key = api_key or settings.azure_openai_api_key
        self.deployment = deployment or settings.azure_openai_chat_deployment
        self.api_version = api_version or settings.azure_openai_api_version
        if not self.endpoint or not self.api_key or not self.deployment:
            raise AdapterError("internal", "missing_azure_openai_config", "Azure OpenAI is not configured.")
        self.settings = settings

    def _request_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/"
            f"{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "messages": messages,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        timeout = float(self.settings.azure_openai_chat_timeout_seconds)
        try:
            response = httpx.post(url, headers=headers, json=body, timeout=timeout)
        except httpx.TimeoutException as exc:
            raise AdapterError(
                "transient",
                "azure_openai_timeout",
                "Azure OpenAI did not finish within the configured time limit. "
                "Quick-start will retry automatically; if this keeps happening, raise "
                "AZURE_OPENAI_CHAT_TIMEOUT_SECONDS or try a shorter script input.",
            ) from exc
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

    def synthesize_brief(
        self,
        *,
        idea_prompt: str,
        starter_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        instruction = (
            "Return JSON with keys title and brief. title must be a concise project title under 80 characters. "
            "brief must be an object with objective, hook, target_audience, call_to_action, brand_north_star, "
            "guardrails, must_include, and approval_steps. guardrails, must_include, and approval_steps must be arrays "
            "of short strings. Use the idea prompt as the primary source of truth and use starter metadata only as style "
            "guidance. Do not mention internal system names."
        )
        user_prompt = json.dumps(
            {
                "idea_prompt": idea_prompt,
                "starter_context": starter_context or {},
            }
        )
        return self._request_json(
            [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_prompt},
            ]
        )["output"]

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

    def generate_scene_plan(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
        script_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
        voice_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        instruction = (
            "Return JSON with keys scene_count, estimated_duration_seconds, validation_warnings, and scenes. "
            "scenes must be an ordered list of 5-8 second scene objects based on the approved script. "
            "Each scene object must include scene_index, source_line_ids, title, beat, narration_text, "
            "caption_text, visual_direction, shot_type, motion, target_duration_seconds, "
            "estimated_voice_duration_seconds, visual_prompt, start_image_prompt, end_image_prompt, "
            "transition_mode, notes, and validation_warnings."
        )
        user_prompt = json.dumps(
            {
                "brief": brief_payload,
                "selected_idea": selected_idea,
                "script": script_payload,
                "visual_preset": visual_preset,
                "voice_preset": voice_preset,
            }
        )
        return self._request_json(
            [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_prompt},
            ]
        )["output"]

    def generate_prompt_pairs(
        self,
        *,
        scene_plan_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        instruction = (
            "Return JSON with one key named segments. segments must be an ordered list matching the input scene order. "
            "Each item must include scene_index, visual_prompt, start_image_prompt, end_image_prompt, and "
            "validation_warnings. Preserve 5-8 second pacing and make prompt pairs visually consistent."
        )
        user_prompt = json.dumps(
            {
                "scene_plan": scene_plan_payload,
                "visual_preset": visual_preset,
            }
        )
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


class OllamaTextProvider(TextProvider):
    def __init__(self, *, endpoint: str, model_name: str) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name or "llama3"
        if not self.endpoint:
            raise AdapterError("internal", "missing_ollama_config", "Ollama endpoint is not configured.")

    def _request_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        url = f"{self.endpoint}/v1/chat/completions"
        body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "stream": False,
            "format": "json",
        }
        try:
            response = httpx.post(url, json=body, timeout=120.0)
        except httpx.TimeoutException as exc:
            raise AdapterError(
                "transient",
                "ollama_timeout",
                "Ollama did not respond within the time limit. Ensure the model is loaded and the endpoint is reachable.",
            ) from exc
        except httpx.ConnectError as exc:
            raise AdapterError(
                "transient",
                "ollama_unreachable",
                f"Cannot connect to Ollama at {self.endpoint}. Ensure Ollama is running.",
            ) from exc
        if response.status_code >= 500:
            raise AdapterError("transient", "ollama_unavailable", "Ollama returned a server error.")
        if response.status_code >= 400:
            raise AdapterError("deterministic_input", "ollama_invalid_request", response.text)

        payload = response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:
            logger.exception("ollama_parse_failure")
            raise AdapterError("internal", "ollama_parse_failure", "Failed to parse Ollama response.") from exc
        return {"output": parsed, "raw": payload}

    def synthesize_brief(self, *, idea_prompt: str, starter_context: dict[str, Any] | None) -> dict[str, Any]:
        instruction = (
            "Return JSON with keys title and brief. title must be a concise project title under 80 characters. "
            "brief must be an object with objective, hook, target_audience, call_to_action, brand_north_star, "
            "guardrails, must_include, and approval_steps. guardrails, must_include, and approval_steps must be arrays "
            "of short strings. Use the idea prompt as the primary source of truth and use starter metadata only as style "
            "guidance. Do not mention internal system names."
        )
        user_prompt = json.dumps({"idea_prompt": idea_prompt, "starter_context": starter_context or {}})
        return self._request_json([
            {"role": "system", "content": instruction},
            {"role": "user", "content": user_prompt},
        ])["output"]

    def generate_ideas(self, brief_payload: dict[str, Any]) -> dict[str, Any]:
        instruction = (
            "Return JSON with exactly one key named ideas. ideas must be a list of exactly 5 items. "
            "Each item must contain title, hook, summary, and tags. The concepts must target a 60-120 second video."
        )
        return self._request_json([
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(brief_payload)},
        ])["output"]

    def generate_script(self, *, brief_payload: dict[str, Any], selected_idea: dict[str, Any]) -> dict[str, Any]:
        instruction = (
            "Return JSON with keys estimated_duration_seconds, reading_time_label, and lines. "
            "lines must be an ordered list of beat objects for a 60-120 second video. "
            "Each line requires id, scene_id, beat, narration, caption, duration_sec, status, visual_direction, voice_pacing."
        )
        return self._request_json([
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps({"brief": brief_payload, "selected_idea": selected_idea})},
        ])["output"]

    def generate_scene_plan(
        self,
        *,
        brief_payload: dict[str, Any],
        selected_idea: dict[str, Any],
        script_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
        voice_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        instruction = (
            "Return JSON with keys scene_count, estimated_duration_seconds, validation_warnings, and scenes. "
            "scenes must be an ordered list of 5-8 second scene objects based on the approved script. "
            "Each scene object must include scene_index, source_line_ids, title, beat, narration_text, "
            "caption_text, visual_direction, shot_type, motion, target_duration_seconds, "
            "estimated_voice_duration_seconds, visual_prompt, start_image_prompt, end_image_prompt, "
            "transition_mode, notes, and validation_warnings."
        )
        return self._request_json([
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps({
                "brief": brief_payload, "selected_idea": selected_idea,
                "script": script_payload, "visual_preset": visual_preset, "voice_preset": voice_preset,
            })},
        ])["output"]

    def generate_prompt_pairs(
        self,
        *,
        scene_plan_payload: dict[str, Any],
        visual_preset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        instruction = (
            "Return JSON with one key named segments. segments must be an ordered list matching the input scene order. "
            "Each item must include scene_index, visual_prompt, start_image_prompt, end_image_prompt, and "
            "validation_warnings. Preserve 5-8 second pacing and make prompt pairs visually consistent."
        )
        return self._request_json([
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps({"scene_plan": scene_plan_payload, "visual_preset": visual_preset})},
        ])["output"]


def build_moderation_provider(settings: Settings) -> ModerationProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubModerationProvider()
    return AzureContentSafetyProvider(settings)


def build_text_provider(settings: Settings) -> TextProvider:
    if settings.use_stub_providers or settings.environment == "test":
        return StubTextProvider()
    return AzureOpenAITextProvider(settings)
