# FastAPI Backend Architecture

## Backend Stack

- FastAPI for HTTP and SSE endpoints
- Pydantic v2 for request and response models
- SQLAlchemy 2.x for ORM and database access
- Alembic for schema migrations
- Celery for background jobs
- Redis as the Celery broker and ephemeral cache

## Service Layers

### API Layer

- Authentication and session endpoints
- Workspace and project endpoints
- Script and scene planning endpoints
- Render, export, billing, and admin endpoints
- SSE endpoints for render progress

**Layer Rule:** Route handlers must not contain business logic. Their only responsibilities are: validate the incoming request shape, call one service method, and return a response. Any conditional logic, database calls, or provider interactions belong in a service, not a route handler.

### Domain Services

- Auth service
- Workspace service
- Project service
- Script service
- Scene planning service
- Preset service
- Template service
- Visual consistency service
- Render orchestration service
- Usage and billing service
- Notification service
- Review service
- Webhook service
- Workspace API key service
- Local worker service
- Export service
- Moderation service

### Worker Services

- Idea and script generation worker
- Scene plan preparation worker
- Asset generation workers by modality (image, video, narration, music)
- Subtitle and timing worker
- FFmpeg composition worker
- Notification delivery worker
- Webhook delivery worker
- Cleanup and retention worker

### Scheduled Workers (Celery Beat)

Background maintenance jobs are owned by Celery Beat and must be explicitly named and scheduled:

| Job Name | Schedule | Purpose |
|---|---|---|
| `reconcile_usage_vs_billing` | Every 1 hour | Align provider run costs with billing ledger |
| `expire_stale_render_jobs` | Every 15 minutes | Transition abandoned jobs to failed state |
| `process_keyframe_review_timeouts` | Every 1 hour | Send reminder notifications and fail overdue keyframe reviews |
| `cleanup_expired_assets` | Every 24 hours | Delete intermediate assets past retention window |
| `archive_old_quarantine_records` | Weekly | Move old moderation quarantine records to cold storage |
| `refresh_worker_health` | Every 5 minutes (Phase 7) | Expire offline local worker registrations |

## Module Boundaries

- `api/` for routes and transport models
- `services/` for business logic
- `models/` for ORM entities
- `schemas/` for Pydantic models
- `workers/` for async task definitions
- `integrations/` for provider adapters
- `core/` for config, auth, logging, and utilities

## Suggested Backend Folder Structure

```text
app/
  api/
    routes/
    deps/
  schemas/
  models/
  services/
  integrations/
    providers/
    billing/
    notifications/
    moderation/
    auth/
    workers/
  workers/
    tasks/
    beat/
  core/
  db/
    migrations/
  tests/
```

- `api/routes` groups endpoints by domain rather than by HTTP verb.
- `services` owns business rules and orchestration decisions.
- `integrations/providers` owns adapter interfaces and concrete provider implementations.
- `integrations/moderation` owns the moderation provider adapter.
- `integrations/notifications` owns email and webhook delivery adapters.
- `integrations/auth` owns password reset, token signing, and session helpers if separated from `core`.
- `integrations/workers` owns local worker protocol helpers and signed-upload orchestration.
- `workers/tasks` owns Celery tasks and step execution logic.
- `workers/beat` owns Celery Beat schedule definitions.
- `core` owns configuration, auth helpers, logging, and shared utilities.
- `db` owns session management and Alembic migrations.

## Database Session Strategy

API requests and Celery workers use distinct session management strategies:

- **API requests:** Use async SQLAlchemy sessions via FastAPI's `Depends` mechanism. One async session per HTTP request, automatically committed or rolled back at the end of the request lifecycle using an `asyncpg` driver.
- **Celery workers:** Use synchronous SQLAlchemy sessions with explicit lifecycle management. Workers open a session at task start, commit it on success, roll back on exception, and close it in a `finally` block. Workers must not use FastAPI's `Depends` for session injection — they manage sessions directly.
- **Connection pool:** Configure separate pool sizes for the API (high concurrency, short-lived connections) and worker pools (fewer connections, longer-lived). Recommended initial values: API pool size 20, worker pool size 5 per worker process.

## API Design Rules

- Sync endpoints should create or mutate product state quickly and return stable references.
- Long-running work should return job identifiers and status endpoints instead of blocking.
- Domain objects should expose version identifiers so the frontend can differentiate drafts from approved versions.
- Admin and internal operations should be separated from public app routes.

## Worker Design Rules

- Workers receive small, explicit payloads rather than entire object graphs.
- Workers must be idempotent and checkpoint progress per step.
- Failure metadata must be captured in a format the product can display to the user and the ops team.
- Providers are only called through adapter interfaces defined in the integrations layer.
- Workers write step results (status, asset references, cost) directly to PostgreSQL and S3 — they do not call the API for routine step updates.

## Authorization Model

- Workspace-scoped roles: `admin`, `member`, `reviewer`, `viewer`
- Project-level ownership checks enforced in service layer
- Admin-only operational endpoints separated under `/admin/` prefix
- Role definitions and detailed permission rules documented in `12-authentication-and-identity.md`

## Operational Concerns

- Centralized structured logging with correlation IDs through all layers
- Correlation identifiers across HTTP requests, job executions, and provider calls
- Rate limiting middleware on API endpoints — see `11-rate-limiting-and-quota-enforcement.md`
- Background reconciliation jobs owned explicitly by Celery Beat as listed above

