# Backend-Frontend Integration Overview

## Goal
- Replace frontend mock-driven flows with real backend APIs while preserving the existing development-only static login experience.
- Move provider and API-key management into workspace-admin-managed platform settings.
- Keep the integration path documented phase by phase so remaining work can proceed without re-deciding contracts.

## Status At Sync Time
- Core live integration is already in place for auth/session, shell data, project workflow, renders/exports, provider settings, local workers, brand kits, scene comments, and template cloning.
- The docs in this folder are now synced to the current implementation state and call out only the remaining gaps that still need follow-up.

## Non-Goals
- Do not introduce a new production-grade auth product or external identity provider flow in this pass.
- Do not broadly refactor unrelated frontend layout, routing, or design-system code.
- Do not delete all mock code before the live path is fully verified and isolated.

## Current Repo Anchors
- Frontend live/mock switch: [frontend/src/lib/config.ts](f:/my-projects/reels-generation/frontend/src/lib/config.ts)
- Frontend fetch wrapper: [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts)
- Frontend live adapter layer: [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts)
- Frontend auth/session bridge: [frontend/src/lib/auth.tsx](f:/my-projects/reels-generation/frontend/src/lib/auth.tsx)
- Frontend mock wrapper still used as a compatibility layer: [frontend/src/lib/mock-service.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-service.ts)
- Frontend legacy mock data layer: [frontend/src/lib/mock-api.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-api.ts)
- Frontend provider UI: [frontend/src/features/settings/ProviderSettingsPage.tsx](f:/my-projects/reels-generation/frontend/src/features/settings/ProviderSettingsPage.tsx)
- Backend API router: [backend/app/api/router.py](f:/my-projects/reels-generation/backend/app/api/router.py)
- Backend auth routes: [backend/app/api/routes/auth.py](f:/my-projects/reels-generation/backend/app/api/routes/auth.py)
- Backend workspace and provider config routes: [backend/app/api/routes/workspace.py](f:/my-projects/reels-generation/backend/app/api/routes/workspace.py)
- Backend render routes: [backend/app/api/routes/renders.py](f:/my-projects/reels-generation/backend/app/api/routes/renders.py)
- Backend comment service: [backend/app/services/comment_service.py](f:/my-projects/reels-generation/backend/app/services/comment_service.py)
- Backend provider credential service: [backend/app/services/provider_credential_service.py](f:/my-projects/reels-generation/backend/app/services/provider_credential_service.py)
- Backend provider capability rules: [backend/app/services/provider_capabilities.py](f:/my-projects/reels-generation/backend/app/services/provider_capabilities.py)
- Backend routing/execution services: [backend/app/services/routing_service.py](f:/my-projects/reels-generation/backend/app/services/routing_service.py), [backend/app/services/execution_policy_service.py](f:/my-projects/reels-generation/backend/app/services/execution_policy_service.py)
- Backend settings and encryption key resolution: [backend/app/core/config.py](f:/my-projects/reels-generation/backend/app/core/config.py)
- App bootstrap and CORS setup: [backend/app/main.py](f:/my-projects/reels-generation/backend/app/main.py)
- Docker and env setup: [infra/compose/docker-compose.yml](f:/my-projects/reels-generation/infra/compose/docker-compose.yml), [infra/env/backend.env](f:/my-projects/reels-generation/infra/env/backend.env), [infra/env/frontend.env](f:/my-projects/reels-generation/infra/env/frontend.env)

## Locked Decisions
- Development auth uses the existing backend login/session flow with the seeded account from [backend/app/cli.py](f:/my-projects/reels-generation/backend/app/cli.py), not a bypass endpoint.
- The login page stays intentionally simple and development-oriented.
- Workspace-scoped provider credentials plus workspace execution policy remain the platform-managed API key architecture.
- Secrets remain server-side only; the frontend can create, update, revoke, and view masked metadata, but it cannot retrieve raw secrets after save.
- Azure OpenAI is the intended text-generation BYO route, while other provider entries can be stored now and expanded at runtime as adapters are added.

## Required Local Stack
- Frontend in live mode via [infra/env/frontend.env](f:/my-projects/reels-generation/infra/env/frontend.env)
- Backend API and workers from [infra/compose/docker-compose.yml](f:/my-projects/reels-generation/infra/compose/docker-compose.yml)
- Postgres, Redis, MinIO, Mailpit from the same compose stack
- Alembic migrations and seed data via [backend/README.md](f:/my-projects/reels-generation/backend/README.md)

## Current State Summary
- CORS for browser cookie auth is implemented in [backend/app/main.py](f:/my-projects/reels-generation/backend/app/main.py).
- Nested backend error envelopes are normalized in [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts).
- Project-scoped render listing is available through the backend render layer.
- Provider credential update support is implemented on the backend and wired into the frontend provider settings page.
- A persistent development encryption key is set in [infra/env/backend.env](f:/my-projects/reels-generation/infra/env/backend.env).
- Several screens still pass through `mock-service.ts` as a compatibility adapter, even though the live path underneath now uses backend APIs.

## Remaining Risks
- The live path is not yet fully isolated from `mock-service.ts` and `mock-api.ts`, which makes future maintenance noisier than it needs to be.
- Provider credential validation is not yet a dedicated backend-validated flow with persisted validation status.
- Admin/workspace screens still do not align 1:1 with backend admin contracts.
- Not all stored provider options are routable at runtime yet; some are storage-only until provider adapters are added.

## Phase Execution Order
1. `01-current-state-analysis.md`
2. `02-api-contract-and-gap-analysis.md`
3. `03-frontend-service-layer-integration.md`
4. `04-auth-integration-with-static-login.md`
5. `05-platform-configurable-api-key-management.md`
6. `06-end-to-end-integration-and-state-handling.md`
7. `07-testing-validation-and-cleanup.md`
8. `08-final-checklist.md`

## Recommended Execution Sequence From Here
1. Finish doc sync and use it as the implementation truth source
2. Isolate remaining live-path dependencies away from `mock-service.ts` and `mock-api.ts`
3. Add provider credential validation behavior and surfaced validation status
4. Align or trim admin/workspace screens to current backend capabilities
5. Expand backend/provider runtime adapters beyond the currently supported BYO paths
6. Run fuller backend/frontend test coverage and Docker smoke verification
