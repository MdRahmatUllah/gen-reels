# Final Checklist

## Documentation Sync Checklist
- [x] `docs/backend-frontend-integration-phase/00-overview.md` through `08-final-checklist.md` reviewed and synced to current implementation
- [x] Current implementation status separated from remaining follow-up work

## Backend Readiness Checklist
- [x] Backend seed credentials chosen and aligned with login page defaults
- [x] `APP_ENCRYPTION_KEY` made persistent in backend env
- [x] CORS implemented for browser cookie auth
- [x] Error response handling contract normalized for the frontend client
- [x] Project render list or equivalent summary route added
- [x] Provider credential update endpoint added
- [x] Provider credential validation behavior added
- [x] Any required admin workspace summary contract added or frontend admin scope trimmed

## Frontend Readiness Checklist
- [x] `api-client.ts` handles nested backend error envelopes
- [x] Auth provider uses backend login/session/logout
- [x] Shell data is live-backed
- [x] Core workflow screens are live-backed in live mode
- [x] Provider settings page uses provider credentials plus execution policy
- [x] Local worker page uses backend worker data
- [x] Brand kits are live-backed
- [x] Scene comments are live-backed
- [x] Template cloning is live-backed
- [x] Hooks under `frontend/src/hooks` no longer depend on `mock-service.ts` in the live path
- [x] Legacy route pages no longer depend on `mock-api.ts` in the live path

## Verification Checklist
- [x] Frontend build passes
- [x] Backend module compile check passes
- [ ] Backend tests for auth/CORS/provider credentials pass
- [ ] Frontend mapper and smoke tests pass
- [ ] Docker live-mode login works
- [x] Brief -> ideas -> script -> scenes -> renders -> exports works in live mode
- [x] Workspace switch updates backend-backed shell state
- [x] Provider credential create/update/revoke works from UI
- [x] Provider credential validate works from UI with persisted status, provider error details, and remote Azure connectivity checks for supported providers
- [x] No raw secret is exposed in list/detail responses

## Mock Cleanup Checklist
- [x] `components/ui.tsx` no longer reads shell data from local-only mocks
- [x] Hooks under `frontend/src/hooks` no longer use `mock-service.ts` as a compatibility layer for live mode
- [x] Legacy route pages no longer use `mock-api.ts` for live mode
- [ ] Remaining mock code, if any, is explicitly isolated for mock-only mode

## Rollout Smoke Test
- [ ] `docker compose up --build`
- [ ] `docker compose exec api uv run alembic upgrade head`
- [ ] `docker compose exec api uv run reels-cli seed`
- [ ] Login succeeds with fixed dev account
- [ ] Session persists across refresh
- [x] Provider settings are manageable from the platform UI
- [x] Render and export data come from backend APIs, not local mock state
- [x] Brand kits, template cloning, and scene comments use backend APIs in live mode

## Definition of Done
- The frontend can operate in live mode through the real backend for the target creator workflow and current settings/collaboration screens.
- Static dev login is preserved as a simple seeded backend login flow.
- Platform-managed provider credentials are implemented as the backend-owned source of runtime secrets.
- The remaining work is now narrow and explicit: admin alignment, further mock-wrapper cleanup, broader provider runtime support, and fuller automated verification.
