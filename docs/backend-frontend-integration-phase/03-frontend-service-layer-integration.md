# Frontend Service Layer Integration

## Objective
- Keep one real backend adapter boundary around [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts) and [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts) so pages continue consuming UI-shaped data instead of raw backend DTOs.

## Service Layer Rules
- Keep components and pages UI-shaped; do not make them parse backend snake_case contracts directly.
- Centralize backend DTO reshaping in the live adapter layer.
- Keep TanStack Query as the owner of server-authoritative state.
- Avoid unrelated UI refactors while continuing the data-source migration.

## Actual Frontend Structure In Use
- [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts): low-level request logic, credentials handling, error normalization
- [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts): endpoint-specific live calls plus DTO-to-UI mapping
- [frontend/src/lib/provider-catalog.ts](f:/my-projects/reels-generation/frontend/src/lib/provider-catalog.ts): provider/type/model metadata used by the settings UI
- [frontend/src/lib/mock-service.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-service.ts): transitional compatibility layer that routes to live adapters in live mode
- `mock-api.ts`: retired after the legacy route layer was moved onto the shared service path

## Query Key Strategy In Practice
- `["auth", "session"]`
- `["shell-data"]`
- `["projects"]`
- `["project", projectId]`
- `["brief", projectId]`
- `["ideas", projectId]`
- `["scripts", projectId]`
- `["scenePlan", projectId]`
- `["renders", projectId]`
- `["render", renderJobId]`
- `["renderEvents", renderJobId]`
- `["exports", projectId]`
- `["billing"]`
- `["providerCredentials"]`
- `["executionPolicy"]`
- `["localWorkers"]`
- `["admin", "renders"]`
- `["admin", "moderation"]`

## What Is Already Migrated

### Shared Foundations
- Nested backend error envelopes are normalized in [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts).
- Live backend mapping is centralized in [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts).

### Shell and Auth
- [frontend/src/lib/auth.tsx](f:/my-projects/reels-generation/frontend/src/lib/auth.tsx) is backend-authenticated in live mode.
- [frontend/src/components/ui.tsx](f:/my-projects/reels-generation/frontend/src/components/ui.tsx) now derives shell state from backend-backed data and workspace selection.

### Creator Workflow
- Project, brief, ideas, scripts, scenes, renders, and exports now flow through live adapters in live mode.
- The workflow pages preserve their current UI contract while relying on adapter-mapped backend responses.

### Settings and Collaboration
- Provider settings, local workers, brand kits, comments, and template cloning are live-backed.

## Remaining Migration Work

### Compatibility Layer Cleanup
- Remove direct live-path dependence on [frontend/src/lib/mock-service.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-service.ts) where hooks can call `live-api.ts` directly.
- Keep mock mode only as an explicit alternate adapter path.

### Legacy Route Cleanup
- Keep legacy pages routed through the same live services/hooks already used by feature pages.
- Avoid reintroducing a second mock adapter layer after retiring `mock-api.ts`.

### Test Coverage
- Add focused mapper tests around auth, project summaries, render summaries, provider credentials, and local workers.

## Async Generation Handling
- `ideas:generate`, `scripts:generate`, `scene-plan:generate`, `generate-prompt-pairs`, and render creation now follow mutation -> accepted job -> query refetch.
- Continue treating accepted-job responses as state transitions, not final content payloads.

## Do Not Refactor Rule
- No unrelated component extraction
- No redesign of page layouts
- No routing reshuffle
- No broad type-system rewrite
- No full mock deletion until the live path is verified and isolated
