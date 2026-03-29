from __future__ import annotations

HOSTED_DEFAULT_PROVIDER_KEYS_BY_MODALITY: dict[str, str] = {
    "text": "azure_openai_text",
    "moderation": "azure_content_safety",
    "image": "azure_openai_image",
    "video": "veo_video",
    "speech": "azure_openai_speech",
}

BYO_RUNTIME_PROVIDER_KEYS_BY_MODALITY: dict[str, set[str]] = {
    "text": {"azure_openai_text"},
    "moderation": {"azure_content_safety"},
    "image": {"azure_openai_image", "stability_image"},
    "video": {"runway_video"},
    "speech": {"azure_openai_speech", "elevenlabs_speech"},
}


def supports_runtime_byo(modality: str, provider_key: str) -> bool:
    return provider_key in BYO_RUNTIME_PROVIDER_KEYS_BY_MODALITY.get(modality, set())
