from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

import httpx
from cryptography.fernet import InvalidToken
from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.crypto import decrypt_json, encrypt_json
from app.core.errors import ApiError
from app.models.entities import ExecutionMode, WorkspaceExecutionPolicy, WorkspaceProviderCredential
from app.schemas.execution import ProviderCredentialCreateRequest, ProviderCredentialUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.provider_capabilities import HOSTED_DEFAULT_PROVIDER_KEYS_BY_MODALITY
from app.services.permissions import require_workspace_admin


class ProviderCredentialService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    @staticmethod
    def _validation_metadata(public_config: dict[str, object] | None) -> dict[str, object]:
        if not isinstance(public_config, dict):
            return {}
        metadata = public_config.get("_validation")
        return metadata if isinstance(metadata, dict) else {}

    def _public_config_for_response(self, credential: WorkspaceProviderCredential) -> dict[str, object]:
        public_config = dict(credential.public_config or {})
        public_config.pop("_validation", None)
        return public_config

    def _reset_validation_metadata(self, credential: WorkspaceProviderCredential) -> None:
        public_config = dict(credential.public_config or {})
        public_config["_validation"] = {
            "status": "not_validated",
            "last_validated_at": None,
            "last_validation_error": None,
        }
        credential.public_config = public_config

    def _set_validation_metadata(
        self,
        credential: WorkspaceProviderCredential,
        *,
        status: str,
        validated_at: datetime,
        error_message: str | None,
    ) -> None:
        public_config = dict(credential.public_config or {})
        public_config["_validation"] = {
            "status": status,
            "last_validated_at": validated_at.isoformat(),
            "last_validation_error": error_message,
        }
        credential.public_config = public_config

    def _to_dict(self, credential: WorkspaceProviderCredential) -> dict[str, object]:
        validation = self._validation_metadata(credential.public_config)
        validation_status = validation.get("status") or "not_validated"
        last_validated_at = validation.get("last_validated_at")
        last_validation_error = validation.get("last_validation_error")
        if credential.secret_payload_encrypted:
            try:
                self._decrypt_secret_config(credential)
            except ApiError as exc:
                validation_status = "invalid"
                last_validation_error = exc.message
        return {
            "id": credential.id,
            "workspace_id": credential.workspace_id,
            "created_by_user_id": credential.created_by_user_id,
            "name": credential.name,
            "modality": credential.modality,
            "provider_key": credential.provider_key,
            "public_config": self._public_config_for_response(credential),
            "last_used_at": credential.last_used_at,
            "expires_at": credential.expires_at,
            "revoked_at": credential.revoked_at,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
            "secret_configured": bool(credential.secret_payload_encrypted),
            "validation_status": validation_status,
            "last_validated_at": last_validated_at,
            "last_validation_error": last_validation_error,
        }

    @staticmethod
    def _undecryptable_secret_message() -> str:
        return (
            "The stored provider secret can no longer be decrypted with the current APP_ENCRYPTION_KEY. "
            "Re-enter the API key for this credential or restore the previous encryption key."
        )

    def _decrypt_secret_config(self, credential: WorkspaceProviderCredential) -> dict[str, object]:
        if not credential.secret_payload_encrypted:
            return {}
        try:
            return decrypt_json(self.settings, credential.secret_payload_encrypted)
        except InvalidToken as exc:
            raise ApiError(
                409,
                "provider_secret_unreadable",
                self._undecryptable_secret_message(),
            ) from exc

    @staticmethod
    def _looks_like_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _validate_secret_and_config(
        self,
        credential: WorkspaceProviderCredential,
        secret_config: dict[str, object],
    ) -> list[str]:
        errors: list[str] = []
        api_key = str(secret_config.get("api_key") or "").strip()
        public_config = dict(credential.public_config or {})
        endpoint = str(public_config.get("endpoint") or "").strip()
        api_version = str(public_config.get("api_version") or "").strip()
        deployment = str(public_config.get("deployment") or "").strip()
        model_name = str(public_config.get("model_name") or public_config.get("model") or "").strip()

        _no_secret_providers = {"ollama_text"}
        if not api_key and credential.provider_key not in _no_secret_providers:
            errors.append("API key is missing.")

        if credential.provider_key == "ollama_text":
            if not endpoint:
                errors.append("Endpoint is required for Ollama credentials.")
            elif not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
        elif credential.provider_key.startswith("azure_openai"):
            if not endpoint:
                errors.append("Endpoint is required for Azure OpenAI credentials.")
            elif not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
            elif "azure.com" not in endpoint:
                errors.append("Azure OpenAI endpoint should target an Azure host.")
            if not api_version:
                errors.append("API version is required for Azure OpenAI credentials.")
            if credential.modality in {"text", "image", "speech"} and not (deployment or model_name):
                errors.append("Provide a deployment name or model name for Azure OpenAI runtime use.")
        elif credential.provider_key == "azure_content_safety":
            if not endpoint:
                errors.append("Endpoint is required for Azure Content Safety credentials.")
            elif not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
            elif "azure.com" not in endpoint:
                errors.append("Azure Content Safety endpoint should target an Azure host.")
        elif credential.provider_key == "stability_image":
            if endpoint and not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
        elif credential.provider_key == "elevenlabs_speech":
            if endpoint and not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
            if not str(public_config.get("voice") or "").strip():
                errors.append("Voice is required for ElevenLabs speech credentials.")
        elif credential.provider_key == "runway_video":
            if endpoint and not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
            if not model_name:
                errors.append("Model name is required for Runway video credentials.")
        elif endpoint and not self._looks_like_url(endpoint):
            errors.append("Endpoint must be a valid http or https URL.")

        return errors

    @staticmethod
    def _validation_probe_error(response: httpx.Response) -> str | None:
        status_code = response.status_code
        response_text = response.text.strip()
        lowered = response_text.lower()

        if status_code < 400:
            return None
        if status_code in {401, 403}:
            return "The provider rejected the supplied API key."
        if status_code == 404:
            return "The configured endpoint, deployment, or API version could not be found."
        if status_code in {400, 405, 422}:
            if any(
                token in lowered
                for token in (
                    "api-version",
                    "unsupported api version",
                    "deployment not found",
                    "resource not found",
                    "no route matched",
                )
            ):
                return "The configured endpoint, deployment, or API version was rejected by the provider."
            if any(
                token in lowered
                for token in (
                    "missing",
                    "required",
                    "invalid request",
                    "expected",
                    "must provide",
                    "body",
                    "json",
                    "voice",
                    "prompt",
                    "messages",
                    "input",
                )
            ):
                return None
        if status_code >= 500:
            return "The provider is temporarily unavailable, so validation could not complete."
        return response_text[:300] if response_text else f"Validation failed with HTTP {status_code}."

    @staticmethod
    def _normalize_azure_endpoint(raw_endpoint: str) -> str:
        """Normalize an Azure endpoint to just scheme://host.

        Users often paste the full curl URL from Azure docs (including
        /openai/deployments/…/images/generations?api-version=…) into the
        endpoint field.  Strip the path *and* query string so the code can
        append the correct path later without doubling it.
        """
        endpoint = raw_endpoint.strip().rstrip("/")
        parsed = urlparse(endpoint)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            # Include query: rare URLs could carry routing hints; any "/openai/"
            # in path or query means this is a full REST URL, not a resource base.
            path_q = f"{parsed.path or ''}?{parsed.query or ''}".lower()
            if "/openai/" in path_q:
                return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            if parsed.path and parsed.path != "/":
                match = re.match(
                    r"(https?://[^/]+)(/openai/.*)$",
                    endpoint,
                    re.IGNORECASE,
                )
                if match:
                    return match.group(1).rstrip("/")
        return endpoint.rstrip("/")

    @staticmethod
    def _normalize_api_version(raw_version: str) -> str:
        """Strip accidental 'api-version=' or '?api-version=' prefix."""
        version = raw_version.strip().lstrip("?")
        prefix = "api-version="
        while version.lower().startswith(prefix):
            version = version[len(prefix):].strip()
        return version.strip()

    def _azure_endpoint(self, public_config: dict[str, object]) -> str:
        return self._normalize_azure_endpoint(
            str(public_config.get("endpoint") or "")
        )

    @staticmethod
    def _response_mentions_parameter(response: httpx.Response, parameter_name: str) -> bool:
        try:
            payload = response.json()
        except ValueError:
            return parameter_name in response.text
        error = payload.get("error")
        if not isinstance(error, dict):
            return parameter_name in response.text
        return str(error.get("param") or "") == parameter_name or parameter_name in str(error.get("message") or "")

    def _azure_text_validation_response(
        self,
        *,
        endpoint: str,
        api_version: str,
        deployment: str,
        api_key: str,
        token_parameter: str,
    ) -> httpx.Response:
        return httpx.post(
            f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
            headers={
                "api-key": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "messages": [{"role": "user", "content": "Reply with ok."}],
                "temperature": 0,
                token_parameter: 32,
            },
            timeout=20.0,
        )

    def _validate_azure_openai_text(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        endpoint = self._azure_endpoint(public_config)
        api_version = self._normalize_api_version(str(public_config.get("api_version") or ""))
        deployment = str(public_config.get("deployment") or "").strip()
        api_key = str(secret_config.get("api_key") or "").strip()
        try:
            response = self._azure_text_validation_response(
                endpoint=endpoint,
                api_version=api_version,
                deployment=deployment,
                api_key=api_key,
                token_parameter="max_completion_tokens",
            )
        except httpx.TimeoutException:
            return "unreachable", "Azure OpenAI timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"Azure OpenAI could not be reached: {exc}"

        if response.status_code in {400, 422} and self._response_mentions_parameter(
            response,
            "max_completion_tokens",
        ):
            try:
                response = self._azure_text_validation_response(
                    endpoint=endpoint,
                    api_version=api_version,
                    deployment=deployment,
                    api_key=api_key,
                    token_parameter="max_tokens",
                )
            except httpx.TimeoutException:
                return "unreachable", "Azure OpenAI timed out before validation completed."
            except httpx.HTTPError as exc:
                return "unreachable", f"Azure OpenAI could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "Azure OpenAI is temporarily unavailable, so validation could not complete."
        if response.status_code in {400, 422} and (
            "model output limit was reached" in response.text.lower()
            or "max_tokens or model output limit was reached" in response.text.lower()
        ):
            return "valid", None
        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_azure_openai_probe(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
        *,
        path: str,
    ) -> tuple[str, str | None]:
        endpoint = self._azure_endpoint(public_config)
        api_version = self._normalize_api_version(str(public_config.get("api_version") or ""))
        deployment = str(public_config.get("deployment") or "").strip()
        api_key = str(secret_config.get("api_key") or "").strip()
        try:
            response = httpx.post(
                f"{endpoint}/openai/deployments/{deployment}/{path}?api-version={api_version}",
                headers={
                    "api-key": api_key,
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={},
                timeout=20.0,
            )
        except httpx.TimeoutException:
            return "unreachable", "Azure OpenAI timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"Azure OpenAI could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "Azure OpenAI is temporarily unavailable, so validation could not complete."
        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_azure_openai_speech(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        """Validate speech credentials by probing chat/completions with audio modality.

        gpt-audio-* deployments expose speech through the chat completions
        endpoint with ``modalities: ["text", "audio"]``, not ``/audio/speech``.
        We send a minimal request and accept both a 200 (full success) and a
        400-level "content required" error as proof the deployment exists and
        credentials are valid.
        """
        endpoint = self._azure_endpoint(public_config)
        api_version = self._normalize_api_version(str(public_config.get("api_version") or ""))
        deployment = str(public_config.get("deployment") or "").strip()
        api_key = str(secret_config.get("api_key") or "").strip()
        voice = str(public_config.get("voice") or "alloy").strip()

        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        try:
            response = httpx.post(
                url,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [{"role": "user", "content": "Say hello."}],
                    "modalities": ["text", "audio"],
                    "audio": {"voice": voice, "format": "wav"},
                    "max_completion_tokens": 200,
                },
                timeout=30.0,
            )
        except httpx.TimeoutException:
            return "unreachable", "Azure OpenAI speech timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"Azure OpenAI speech could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "Azure OpenAI speech is temporarily unavailable."
        if response.status_code == 200:
            return "valid", None

        body = response.text[:500]
        if "OperationNotSupported" in body or "does not work with the specified model" in body:
            return (
                "invalid",
                "This deployment does not support audio generation via chat completions. "
                "Use a gpt-audio-* deployment or a classic TTS deployment.",
            )

        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_azure_content_safety(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        endpoint = self._azure_endpoint(public_config)
        api_version = str(public_config.get("api_version") or "").strip()
        api_key = str(secret_config.get("api_key") or "").strip()
        try:
            response = httpx.post(
                f"{endpoint}/contentsafety/text:analyze?api-version={api_version}",
                headers={
                    "Ocp-Apim-Subscription-Key": api_key,
                    "Content-Type": "application/json",
                },
                json={"text": "Validation probe"},
                timeout=20.0,
            )
        except httpx.TimeoutException:
            return "unreachable", "Azure Content Safety timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"Azure Content Safety could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "Azure Content Safety is temporarily unavailable, so validation could not complete."
        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_stability_image(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        endpoint = str(public_config.get("endpoint") or "https://api.stability.ai").strip().rstrip("/")
        api_key = str(secret_config.get("api_key") or "").strip()
        try:
            response = httpx.get(
                f"{endpoint}/v1/user/balance",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20.0,
            )
        except httpx.TimeoutException:
            return "unreachable", "Stability AI timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"Stability AI could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "Stability AI is temporarily unavailable, so validation could not complete."
        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_elevenlabs_speech(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        endpoint = str(public_config.get("endpoint") or "https://api.elevenlabs.io").strip().rstrip("/")
        api_key = str(secret_config.get("api_key") or "").strip()
        try:
            response = httpx.get(
                f"{endpoint}/v1/models",
                headers={"xi-api-key": api_key},
                timeout=20.0,
            )
        except httpx.TimeoutException:
            return "unreachable", "ElevenLabs timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"ElevenLabs could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "ElevenLabs is temporarily unavailable, so validation could not complete."
        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_runway_video(
        self,
        public_config: dict[str, object],
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        endpoint = str(public_config.get("endpoint") or "https://api.dev.runwayml.com").strip().rstrip("/")
        api_key = str(secret_config.get("api_key") or "").strip()
        try:
            response = httpx.get(
                f"{endpoint}/v1/tasks/00000000-0000-4000-8000-000000000000",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-Runway-Version": "2024-11-06",
                },
                timeout=20.0,
            )
        except httpx.TimeoutException:
            return "unreachable", "Runway timed out before validation completed."
        except httpx.HTTPError as exc:
            return "unreachable", f"Runway could not be reached: {exc}"

        if response.status_code in {408, 429} or response.status_code >= 500:
            return "unreachable", "Runway is temporarily unavailable, so validation could not complete."
        if response.status_code == 404:
            return "valid", None
        error_message = self._validation_probe_error(response)
        return ("invalid", error_message) if error_message else ("valid", None)

    def _validate_ollama(
        self,
        public_config: dict[str, object],
    ) -> tuple[str, str | None]:
        endpoint = str(public_config.get("endpoint") or "http://host.docker.internal:11434").strip().rstrip("/")
        model_name = str(public_config.get("model_name") or "").strip()
        try:
            # Probe /api/tags to confirm Ollama is reachable
            response = httpx.get(f"{endpoint}/api/tags", timeout=10.0)
        except httpx.TimeoutException:
            return "unreachable", "Ollama did not respond within the time limit. Ensure it is running and the endpoint is correct."
        except httpx.ConnectError:
            return "unreachable", f"Cannot connect to Ollama at {endpoint}. Ensure Ollama is running."
        except httpx.HTTPError as exc:
            return "unreachable", f"Ollama could not be reached: {exc}"

        if response.status_code != 200:
            return "invalid", f"Ollama returned HTTP {response.status_code} on /api/tags."

        # If a model is configured, verify it is in the pulled models list
        if model_name:
            try:
                models = [m["name"] for m in response.json().get("models", [])]
            except Exception:
                models = []
            if models and model_name not in models:
                return "invalid", f"Model '{model_name}' is not in the pulled models list. Run: ollama pull {model_name}"

        return "valid", None

    def _validate_remote_provider(
        self,
        credential: WorkspaceProviderCredential,
        secret_config: dict[str, object],
    ) -> tuple[str, str | None]:
        public_config = dict(credential.public_config or {})
        if credential.provider_key == "azure_openai_text":
            return self._validate_azure_openai_text(public_config, secret_config)
        if credential.provider_key == "azure_openai_image":
            return self._validate_azure_openai_probe(
                public_config,
                secret_config,
                path="images/generations",
            )
        if credential.provider_key == "azure_openai_speech":
            return self._validate_azure_openai_speech(public_config, secret_config)
        if credential.provider_key == "azure_content_safety":
            return self._validate_azure_content_safety(public_config, secret_config)
        if credential.provider_key == "stability_image":
            return self._validate_stability_image(public_config, secret_config)
        if credential.provider_key == "elevenlabs_speech":
            return self._validate_elevenlabs_speech(public_config, secret_config)
        if credential.provider_key == "runway_video":
            return self._validate_runway_video(public_config, secret_config)
        if credential.provider_key == "ollama_text":
            return self._validate_ollama(public_config)
        return (
            "unsupported",
            "Remote validation is not implemented for this provider in the current build.",
        )

    def _credential(
        self,
        workspace_id: str | UUID,
        credential_id: str | UUID,
        *,
        include_revoked: bool = False,
    ) -> WorkspaceProviderCredential:
        credential = self.db.scalar(
            select(WorkspaceProviderCredential).where(
                WorkspaceProviderCredential.id == UUID(str(credential_id)),
                WorkspaceProviderCredential.workspace_id == UUID(str(workspace_id)),
            )
        )
        if not credential:
            raise ApiError(404, "provider_credential_not_found", "Provider credential not found.")
        if not include_revoked:
            self._assert_credential_active(credential)
        return credential

    def _assert_credential_active(self, credential: WorkspaceProviderCredential) -> None:
        now = datetime.now(timezone.utc)
        if credential.revoked_at is not None:
            raise ApiError(400, "provider_credential_revoked", "That provider credential has been revoked.")
        if credential.expires_at is not None and credential.expires_at <= now:
            raise ApiError(400, "provider_credential_expired", "That provider credential has expired.")

    def list_credentials(self, auth: AuthContext) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credentials = self.db.scalars(
            select(WorkspaceProviderCredential)
            .where(WorkspaceProviderCredential.workspace_id == UUID(auth.workspace_id))
            .order_by(WorkspaceProviderCredential.created_at.desc())
        ).all()
        return [self._to_dict(credential) for credential in credentials]

    def _detach_credential_from_policy(
        self,
        workspace_id: UUID,
        credential_id: UUID,
        *,
        replacement_modality: str | None = None,
        replacement_provider_key: str | None = None,
    ) -> None:
        policy = self.db.scalar(
            select(WorkspaceExecutionPolicy).where(WorkspaceExecutionPolicy.workspace_id == workspace_id)
        )
        if not policy:
            return
        for modality in ("text", "moderation", "image", "video", "speech"):
            if getattr(policy, f"{modality}_credential_id") != credential_id:
                continue
            should_keep_binding = (
                replacement_modality == modality
                and replacement_provider_key == getattr(policy, f"{modality}_provider_key")
            )
            if should_keep_binding:
                continue
            setattr(policy, f"{modality}_mode", ExecutionMode.hosted)
            setattr(
                policy,
                f"{modality}_provider_key",
                HOSTED_DEFAULT_PROVIDER_KEYS_BY_MODALITY[modality],
            )
            setattr(policy, f"{modality}_credential_id", None)

    def create_credential(
        self,
        auth: AuthContext,
        payload: ProviderCredentialCreateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        _no_secret_providers = {"ollama_text"}
        if not payload.secret_config and payload.provider_key not in _no_secret_providers:
            raise ApiError(400, "provider_secret_required", "A provider secret payload is required.")
        secret_payload_encrypted = (
            encrypt_json(self.settings, payload.secret_config) if payload.secret_config else None
        )
        credential = WorkspaceProviderCredential(
            workspace_id=UUID(auth.workspace_id),
            created_by_user_id=UUID(auth.user_id),
            name=payload.name,
            modality=payload.modality,
            provider_key=payload.provider_key,
            public_config=payload.public_config,
            secret_payload_encrypted=secret_payload_encrypted,
            expires_at=payload.expires_at,
        )
        self._reset_validation_metadata(credential)
        self.db.add(credential)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_created",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={"modality": credential.modality, "provider_key": credential.provider_key},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def update_credential(
        self,
        auth: AuthContext,
        credential_id: str,
        payload: ProviderCredentialUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id)
        next_modality = payload.modality or credential.modality
        next_provider_key = payload.provider_key or credential.provider_key

        if payload.name is not None:
            credential.name = payload.name
        if payload.modality is not None:
            credential.modality = payload.modality
        if payload.provider_key is not None:
            credential.provider_key = payload.provider_key
        if payload.public_config is not None:
            merged = dict(credential.public_config or {})
            merged.update(payload.public_config)
            credential.public_config = merged
        if payload.secret_config is not None:
            if not payload.secret_config:
                raise ApiError(400, "provider_secret_required", "A provider secret payload is required.")
            credential.secret_payload_encrypted = encrypt_json(self.settings, payload.secret_config)
        if "expires_at" in payload.model_fields_set:
            credential.expires_at = payload.expires_at
        if any(
            field in payload.model_fields_set
            for field in ("modality", "provider_key", "public_config", "secret_config")
        ):
            self._reset_validation_metadata(credential)

        self._detach_credential_from_policy(
            credential.workspace_id,
            credential.id,
            replacement_modality=next_modality,
            replacement_provider_key=next_provider_key,
        )
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_updated",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={"modality": credential.modality, "provider_key": credential.provider_key},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def validate_credential(self, auth: AuthContext, credential_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id)
        validated_at = datetime.now(timezone.utc)
        try:
            secret_config = self._decrypt_secret_config(credential)
        except ApiError as exc:
            self._set_validation_metadata(
                credential,
                status="invalid",
                validated_at=validated_at,
                error_message=exc.message,
            )
            record_audit_event(
                self.db,
                workspace_id=credential.workspace_id,
                user_id=UUID(auth.user_id),
                event_type="workspace.provider_credential_validated",
                target_type="workspace_provider_credential",
                target_id=str(credential.id),
                payload={"status": "invalid", "provider_key": credential.provider_key},
            )
            self.db.commit()
            self.db.refresh(credential)
            return self._to_dict(credential)

        errors = self._validate_secret_and_config(credential, secret_config)
        if errors:
            status = "invalid"
            error_message = "; ".join(errors)
        else:
            status, error_message = self._validate_remote_provider(credential, secret_config)
        self._set_validation_metadata(
            credential,
            status=status,
            validated_at=validated_at,
            error_message=error_message,
        )
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_validated",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={"status": status, "provider_key": credential.provider_key},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def revoke_credential(self, auth: AuthContext, credential_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id, include_revoked=True)
        credential.revoked_at = credential.revoked_at or datetime.now(timezone.utc)
        self._detach_credential_from_policy(credential.workspace_id, credential.id)
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_revoked",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def get_runtime_credential(
        self,
        workspace_id: str | UUID,
        credential_id: str | UUID,
        *,
        modality: str | None = None,
    ) -> tuple[WorkspaceProviderCredential, dict[str, object]]:
        credential = self._credential(workspace_id, credential_id)
        if modality and credential.modality != modality:
            raise ApiError(
                400,
                "provider_credential_modality_mismatch",
                "That provider credential does not match the requested modality.",
            )
        return credential, self._decrypt_secret_config(credential)

    def touch_runtime_use(self, credential: WorkspaceProviderCredential) -> None:
        credential.last_used_at = datetime.now(timezone.utc)
