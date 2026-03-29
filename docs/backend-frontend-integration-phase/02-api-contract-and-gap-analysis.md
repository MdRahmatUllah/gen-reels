# API Contract and Gap Analysis

## Contract Mismatch Summary
- Backend contracts remain richer, normalized, and snake_case-heavy.
- Frontend contracts remain UI-shaped and flatter because they preserve existing page expectations.
- Integration now uses mapper logic in [frontend/src/lib/live-api.ts](f:/my-projects/reels-generation/frontend/src/lib/live-api.ts) and related hook/service adapters instead of teaching components raw backend DTOs.

## Global Contract Status

| Area | Previous Gap | Current Status | Remaining Work |
| --- | --- | --- | --- |
| CORS + cookies | Browser cookie auth blocked from frontend origin | Implemented in [backend/app/main.py](f:/my-projects/reels-generation/backend/app/main.py) | Keep covered by backend tests |
| Error shape | Frontend expected top-level `code` and `message` | Normalized in [frontend/src/lib/api-client.ts](f:/my-projects/reels-generation/frontend/src/lib/api-client.ts) | Add explicit test coverage |
| Auth session shape | Frontend expected a narrower `AuthSession` | Live auth/session mapping is implemented | Continue cleanup of any legacy assumptions |
| Generation flow | Frontend expected sync payloads | Accepted-job and refetch flow is wired for core workflow pages | Add more formal smoke coverage |
| Render listing | Project render list endpoint missing | Implemented through backend render layer | Verify Docker smoke coverage |
| Provider settings | Generic provider-key CRUD did not match backend model | Provider credential plus execution policy flow is implemented | Add validation endpoint/validation-on-save behavior |
| Brand kits | Mock-only settings integration | Live-backed through frontend adapters | Add tests |
| Scene comments | Mock-only and invalid collaboration target | Live-backed; `scene_segment` target implemented | Add tests |
| Template cloning | Mock-only | Live-backed through backend template project creation | Add tests |
| Admin workspace summaries | Frontend expected unavailable aggregate views | Still not aligned | Add backend summary contract or trim frontend scope |

## DTO Mismatches Normalized In Mappers
- `ProjectSummary`: mapped from backend project/profile data into UI-facing summary fields.
- `AuthSession`: mapped from backend `user`, `workspaces`, `active_workspace_id`, and `active_role`.
- `BriefData`: mapped from backend brief/version payloads into the current brief editor model.
- `IdeaSet`: latest/active backend set is projected into the current ideas UI.
- `ScriptData`: backend version payloads are adapted to the current script editor shape.
- `ScenePlanSet`: backend scene-plan and segment data are adapted to the UI scene-card model.
- `RenderJob`: backend render detail and summaries are projected into the current render workflow UI.
- `BillingData`: still requires a combined frontend view over multiple backend sources.
- `ProviderKey`: replaced in practice by provider credential plus execution policy mapping.
- `LocalWorker`: adapted from backend worker capability metadata into the current settings page shape.

## Remaining Backend Additions
- Add provider credential validation endpoint or validation-on-save semantics with persisted validation metadata.
- Add backend tests for CORS, provider credential update and revoke rules, render list behavior, and comment target coverage.
- Add either an admin workspace summary endpoint or reduce the frontend admin scope to match existing backend views.

## Remaining Frontend Gaps
- Remove live-path dependence on [frontend/src/lib/mock-service.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-service.ts) compatibility wrappers where hooks can call live adapters directly.
- Reduce or replace [frontend/src/lib/mock-api.ts](f:/my-projects/reels-generation/frontend/src/lib/mock-api.ts) usage in remaining legacy and admin pages.
- Add mapper-level tests around the most fragile DTO conversions.

## Admin And Settings Notes
- Provider settings are now aligned to modality-aware credentials and execution policy rather than a generic provider-key table.
- The provider UI supports multiple generation types and user-supplied model names, but not every stored provider option is currently supported as an active runtime route.
- Admin queue and admin workspace screens remain the least aligned part of the current integration.
