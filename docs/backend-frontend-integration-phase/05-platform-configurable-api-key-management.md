# Platform-Configurable API Key Management

## Goal
- Replace hardcoded or mock-only provider key handling with workspace-admin-managed provider credentials and execution policy.

## Existing Backend Foundations In Use
- Provider credential storage: [backend/app/models/entities.py](f:/my-projects/reels-generation/backend/app/models/entities.py)
- Workspace credential APIs: [backend/app/api/routes/workspace.py](f:/my-projects/reels-generation/backend/app/api/routes/workspace.py)
- Credential update schema: [backend/app/schemas/execution.py](f:/my-projects/reels-generation/backend/app/schemas/execution.py)
- Encryption helpers: [backend/app/core/crypto.py](f:/my-projects/reels-generation/backend/app/core/crypto.py)
- Credential service: [backend/app/services/provider_credential_service.py](f:/my-projects/reels-generation/backend/app/services/provider_credential_service.py)
- Execution policy service: [backend/app/services/execution_policy_service.py](f:/my-projects/reels-generation/backend/app/services/execution_policy_service.py)
- Provider runtime support rules: [backend/app/services/provider_capabilities.py](f:/my-projects/reels-generation/backend/app/services/provider_capabilities.py)

## Current Implementation Status
- Provider credentials are managed from the platform UI in [frontend/src/features/settings/ProviderSettingsPage.tsx](f:/my-projects/reels-generation/frontend/src/features/settings/ProviderSettingsPage.tsx).
- The UI supports multiple generation types, including text, audio, image, video, and moderation-oriented routing.
- Users can provide provider-specific metadata and model names from the UI.
- Backend create, list, revoke, and update flows are implemented.
- Execution policy updates are wired so supported BYO routes can be activated safely.
- Raw secrets are not returned after save.

## Current UX Model
- Credential list
- create/edit credential form
- revoke action
- per-generation-type execution policy selector
- user-supplied model/deployment metadata
- provider catalog metadata via [frontend/src/lib/provider-catalog.ts](f:/my-projects/reels-generation/frontend/src/lib/provider-catalog.ts)

## Secret Handling Rules
- Raw secret values are accepted only on create or secret replacement.
- Raw secret values are never returned in list/detail responses after save.
- UI displays masked and non-secret metadata only.
- Backend services consume decrypted secrets only at runtime inside routing/provider adapters.

## Storage and Encryption
- Encryption-at-rest remains based on existing Fernet helpers in [backend/app/core/crypto.py](f:/my-projects/reels-generation/backend/app/core/crypto.py).
- A persistent development `APP_ENCRYPTION_KEY` is configured in [infra/env/backend.env](f:/my-projects/reels-generation/infra/env/backend.env), which avoids development restarts invalidating stored secrets.

## Azure OpenAI Position
- Azure OpenAI is the intended text-generation BYO route for this project.
- The provider settings model now supports provider selection plus user-entered model names and deployment-like metadata rather than assuming a single hardcoded provider.
- Azure-focused routing can be selected for text generation through the platform configuration flow.

## Validation Flow In Use
- `POST /api/v1/workspace/provider-credentials/{credential_id}:validate` is implemented and persists validation metadata on the credential record.
- Supported Azure-backed providers perform an outbound backend validation check instead of config-only validation.
- `azure_openai_text` uses a low-cost live chat-completions probe.
- `azure_openai_image` and `azure_openai_speech` use deployment endpoint probes that validate endpoint, API version, deployment path, and API key without activating those routes from the browser.
- `azure_content_safety` performs a live moderation probe against the configured endpoint.
- `stability_image` validates against the Stability account endpoint and is routable for image generation.
- `elevenlabs_speech` validates against the ElevenLabs models endpoint and is routable for narration generation.
- `runway_video` validates against the Runway task API and is routable for image-to-video generation with backend task polling.
- Providers that are currently storage-only in the UI return an explicit `unsupported` validation status rather than a misleading success state.
- Network or provider outages return an explicit `unreachable` validation status so users can distinguish connectivity issues from bad credentials.

## Remaining Gaps
- Expand runtime provider adapters for providers that are currently stored in the UI but not yet fully routable, primarily Kling and any future video providers beyond Runway.

## Development Architecture Rules
- Env provider variables may remain as bootstrap or fallback during transition.
- Once a workspace is configured for BYO on a modality, backend runtime routing should consume the workspace credential rather than any frontend-provided secret.
- Frontend must never send secrets except through explicit admin credential create/update requests.

## Validation Status
- Admin can create, update, and revoke credentials from the UI.
- List and detail responses do not expose raw secret payloads.
- Execution policy can point supported modalities to a saved credential.
- Active policy fallback behavior is handled when a credential is revoked or becomes unsupported.
