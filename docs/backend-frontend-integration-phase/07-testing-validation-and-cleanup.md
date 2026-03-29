# Testing, Validation, and Cleanup

## Validation Already Completed
- `npm run build` passed in `frontend/`
- `python -m compileall backend/app` passed

## Validation Still Recommended

### Backend Test Scope
- Add tests for:
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/session`
  - `POST /api/v1/auth/logout`
  - `POST /api/v1/auth/workspace/select`
  - CORS preflight and credential headers for the frontend origin
  - provider credential create/update/revoke behavior
  - provider validation behavior, including `valid`, `invalid`, `unsupported`, and `unreachable` states
  - non-disclosure of raw secret payload after save
  - render list/detail/cancel/retry compatibility with frontend needs
  - scene comment target handling, including `scene_segment`

### Frontend Validation Scope
- Add tests for:
  - auth bootstrap and protected-route behavior
  - project list and brief update
  - generate idea/script/scene-plan flow with async refetch
  - render create/detail/refetch behavior
  - provider settings save/revoke and persisted validation state display
  - mapper coverage for auth, projects, renders, provider credentials, and local workers

## Manual End-to-End Validation
1. Run `docker compose up --build`
2. Run migrations
3. Seed backend data
4. Confirm backend uses the persistent `APP_ENCRYPTION_KEY`
5. Open frontend in live mode
6. Log in with `admin@example.com / ChangeMe123!`
7. Verify shell and workspace data load from backend
8. Create or update a project brief
9. Generate ideas, select one, generate script, approve script
10. Generate scene plan and prompt pairs
11. Start a render and observe live detail updates
12. Verify exports list loads
13. Create or update a provider credential and bind it in execution policy
14. Verify brand kits, template clone, and scene comments behave against live APIs

## Cleanup Rules
- Do not delete mock code before the live replacement for that screen is verified.
- Cleanup order:
  1. remove direct mock imports from hooks
  2. remove direct mock imports from route pages
  3. remove shell compatibility dependence on mock wrappers
  4. retire dead helper functions from `mock-service.ts`
  5. keep `mock-api.ts` retired
- If mock mode remains supported for UI-only work, keep it as an explicit alternate adapter path.

## Done Criteria For Cleanup
- Live mode path no longer depends on `mock-service.ts` or any retired parallel mock layer.
- Remaining mock code, if any, is intentionally isolated and not accidentally used by live hooks.
- Documentation and README notes reflect the real implemented integration state.
