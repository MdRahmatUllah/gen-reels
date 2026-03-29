from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import Settings


def _fernet(settings: Settings) -> Fernet:
    return Fernet(settings.app_encryption_key_resolved.encode("utf-8"))


def encrypt_text(settings: Settings, value: str) -> str:
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(settings: Settings, value: str) -> str:
    return _fernet(settings).decrypt(value.encode("utf-8")).decode("utf-8")


def encrypt_json(settings: Settings, payload: dict[str, Any]) -> str:
    return encrypt_text(settings, json.dumps(payload, sort_keys=True))


def decrypt_json(settings: Settings, payload: str | None) -> dict[str, Any]:
    if not payload:
        return {}
    return json.loads(decrypt_text(settings, payload))
