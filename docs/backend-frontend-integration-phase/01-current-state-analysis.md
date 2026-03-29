# Current State Analysis

## Frontend Architecture Today

### App Shell and Routing
- Route composition lives in [frontend/src/app/router.tsx](f:/my-projects/reels-generation/frontend/src/app/router.tsx).
- The shell layout in [frontend/src/components/ui.tsx](f:/my-projects/reels-generation/frontend/src/components/ui.tsx) now loads backend-backed auth and shell data in live mode.
- The app is still split between legacy route pages in [frontend/src/routes/app-pages.tsx](f:/my-projects/reels-generation/frontend/src/routes/app-pages.tsx) and feature pages under `frontend/src/features/*`.
- [frontend/src/components/ProtectedRoute.tsx](f:/my-projects/reels-generation/frontend/src/components/ProtectedRoute.tsx) now relies on backend session state through the auth provider.

### Data Access Pattern
- TanStack Query remains the primary server-state abstraction in [frontend/src/app/AppProviders.tsx](f:/my-projects/reels-generation/frontend/src/app/AppProviders.tsx).
- The real backend adapter layer now lives in [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts).
- [frontend/src/lib/mock-service.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-service.ts) still exists, but many live-mode hooks now delegate through it into `live-api.ts` rather than returning local-only mock state.
- Legacy route pages still carry some `mock-api.ts` usage in [frontend/src/lib/mock-api.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-api.ts), so the adapter boundary is improved but not fully cleaned up yet.

### Current Live-Integrated Frontend Areas
- Auth/session: [frontend/src/lib/auth.tsx](f:/my-projects/reels-generation/frontend/src/lib/auth.tsx)
- Shell/workspace sync: [frontend/src/components/ui.tsx](f:/my-projects/reels-generation/frontend/src/components/ui.tsx)
- Core project workflow hooks and pages: `frontend/src/hooks/*`, [frontend/src/features/ideas/IdeasPage.tsx](f:/my-projects/reels-generation/frontend/src/features/ideas/IdeasPage.tsx), [frontend/src/features/scenes/ScenesPage.tsx](f:/my-projects/reels-generation/frontend/src/features/scenes/ScenesPage.tsx), [frontend/src/routes/app-pages.tsx](f:/my-projects/reels-generation/frontend/src/routes/app-pages.tsx)
- Provider settings: [frontend/src/features/settings/ProviderSettingsPage.tsx](f:/my-projects/reels-generation/frontend/src/features/settings/ProviderSettingsPage.tsx), [frontend/src/hooks/use-providers.ts](f:/my-projects/reels-generation/frontend/src/hooks/use-providers.ts), [frontend/src/lib/provider-catalog.ts](f:/my-projects/reels-generation/frontend/src/lib/provider-catalog.ts)
- Brand kits, comments, and template cloning: [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts), [frontend/src/components/CommentThread.tsx](f:/my-projects/reels-generation/frontend/src/components/CommentThread.tsx)

### Auth Flow Today
- [frontend/src/lib/auth.tsx](f:/my-projects/reels-generation/frontend/src/lib/auth.tsx) uses backend login/session/logout in live mode.
- [frontend/src/routes/login-page.tsx](f:/my-projects/reels-generation/frontend/src/routes/login-page.tsx) is aligned to the seeded backend credentials from [backend/app/cli.py](f:/my-projects/reels-generation/backend/app/cli.py): `admin@example.com / ChangeMe123!`.
- Workspace switching is backend-backed through `POST /api/v1/auth/workspace/select`, with client query invalidation after selection.

### Frontend Config
- Live/mock mode is selected through [frontend/src/lib/config.ts](f:/my-projects/reels-generation/frontend/src/lib/config.ts).
- Docker frontend runs in live mode via [infra/env/frontend.env](f:/my-projects/reels-generation/infra/env/frontend.env).
- [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts) is now part of the active path instead of being mostly dormant.

## Backend Architecture Today

### API Structure
- Route registration is centralized in [backend/app/api/router.py](f:/my-projects/reels-generation/backend/app/api/router.py).
- Core route groups already exist for auth, projects, ideas, scripts, scene plans, renders, presets, assets, templates, billing, usage, workspace settings, local workers, comments, reviews, notifications, and admin.
- Backend services remain layered in `backend/app/services/*`.

### Auth and Session
- Cookie-based session auth is implemented in [backend/app/api/routes/auth.py](f:/my-projects/reels-generation/backend/app/api/routes/auth.py) and [backend/app/services/auth_service.py](f:/my-projects/reels-generation/backend/app/services/auth_service.py).
- Browser CORS support for the frontend origin is implemented in [backend/app/main.py](f:/my-projects/reels-generation/backend/app/main.py).
- Session state remains backend-authoritative and workspace-aware.

### Provider and Secret Handling
- Provider credentials exist as a workspace-scoped concept in [backend/app/models/entities.py](f:/my-projects/reels-generation/backend/app/models/entities.py).
- Secrets are encrypted using [backend/app/core/crypto.py](f:/my-projects/reels-generation/backend/app/core/crypto.py).
- Create, list, revoke, and update APIs exist in [backend/app/api/routes/workspace.py](f:/my-projects/reels-generation/backend/app/api/routes/workspace.py).
- Runtime usage is routed through [backend/app/services/routing_service.py](f:/my-projects/reels-generation/backend/app/services/routing_service.py), [backend/app/services/provider_credential_service.py](f:/my-projects/reels-generation/backend/app/services/provider_credential_service.py), and [backend/app/services/execution_policy_service.py](f:/my-projects/reels-generation/backend/app/services/execution_policy_service.py).
- Provider capability and supported BYO runtime rules are centralized in [backend/app/services/provider_capabilities.py](f:/my-projects/reels-generation/backend/app/services/provider_capabilities.py).

### Render, Collaboration, and Generation Model
- Ideas, scripts, scene plans, prompt pairs, and renders are asynchronous backend jobs.
- The frontend now accounts for accepted-job responses and refetches downstream data instead of assuming synchronous payloads.
- Project render listing is available through the backend render layer.
- Scene comments are live-backed, and `scene_segment` is now a valid collaboration target in [backend/app/services/collaboration_targets.py](f:/my-projects/reels-generation/backend/app/services/collaboration_targets.py).

## Docker and Environment Setup
- Canonical compose file: [infra/compose/docker-compose.yml](f:/my-projects/reels-generation/infra/compose/docker-compose.yml)
- Backend image: [infra/docker/backend/Dockerfile](f:/my-projects/reels-generation/infra/docker/backend/Dockerfile)
- Frontend image: [infra/docker/frontend/Dockerfile](f:/my-projects/reels-generation/infra/docker/frontend/Dockerfile)
- Backend env reference: [infra/env/backend.env](f:/my-projects/reels-generation/infra/env/backend.env)
- Frontend env reference: [infra/env/frontend.env](f:/my-projects/reels-generation/infra/env/frontend.env)

## Key Findings
- The frontend already had the right query-oriented shape, which made targeted live adapters practical without a major architectural rewrite.
- The backend already contained most of the domain building blocks needed for provider credential management and workflow execution.
- The biggest improvement so far has been adapter alignment, not domain invention.
- The biggest remaining cleanup work is reducing the compatibility-layer dependence on `mock-service.ts` and trimming legacy pages still tied to `mock-api.ts`.
