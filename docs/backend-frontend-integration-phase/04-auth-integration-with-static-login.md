# Auth Integration With Static Login

## Goal
- Keep the development login UX simple and fixed, while making it backend-authenticated and workspace-aware.

## Current Implementation
- Live mode uses the existing backend auth/session cookies from [backend/app/api/routes/auth.py](f:/my-projects/reels-generation/backend/app/api/routes/auth.py).
- [frontend/src/lib/auth.tsx](f:/my-projects/reels-generation/frontend/src/lib/auth.tsx) uses backend login, session bootstrap, logout, and workspace selection flows.
- [frontend/src/routes/login-page.tsx](f:/my-projects/reels-generation/frontend/src/routes/login-page.tsx) is aligned to the seeded backend credentials from [backend/app/cli.py](f:/my-projects/reels-generation/backend/app/cli.py): `admin@example.com / ChangeMe123!`.
- Browser cookie auth is enabled by CORS middleware in [backend/app/main.py](f:/my-projects/reels-generation/backend/app/main.py).

## Locked Behavior
- Keep cookie auth as the active mechanism.
- Do not add a development-only bypass endpoint.
- Keep the login form minimal and explicitly development-oriented.

## Frontend Flow
- `login()` calls `POST /api/v1/auth/login`
- initial bootstrap calls `GET /api/v1/auth/session`
- `logout()` calls `POST /api/v1/auth/logout`
- workspace switching calls `POST /api/v1/auth/workspace/select`
- auth and shell queries are invalidated after workspace selection

## Current Session Model
- backend user summary
- workspace memberships
- active workspace id
- active role
- loading and error state

## Remaining Follow-Up
- Add backend and frontend tests around login/session/logout/workspace-select behavior.
- Keep checking legacy pages for any stale assumptions about local-only auth state.

## Validation Status
- Session-based login flow is implemented in live mode.
- Refresh persistence is supported by backend cookie auth.
- Workspace switching is backend-backed.
- The development login remains static in UX, but authoritative in data source.
