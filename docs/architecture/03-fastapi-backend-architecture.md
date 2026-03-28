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
- Idea, script, scene planning, and prompt-pair endpoints
- Render, export, billing, and admin endpoints
- SSE endpoints for render progress

### Domain Services

- Auth service
- Workspace service
- Project service
- Idea service
- Script service
- Scene planning service
- Prompt-pair service
- Preset service
- Template service
- Visual continuity service
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
- Scene plan and prompt-pair generation worker
- Frame-pair generation workers by modality
- Video generation workers
- Narration generation workers
- Source-audio stripping worker
- Clip retiming worker
- Music and subtitle workers
- FFmpeg composition worker
- Notification delivery worker
- Webhook delivery worker
- Cleanup and retention worker

### Scheduled Workers (Celery Beat)

| Job Name | Schedule | Purpose |
| --- | --- | --- |
| `reconcile_usage_vs_billing` | Every 1 hour | Align provider run costs with billing ledger |
| `expire_stale_render_jobs` | Every 15 minutes | Transition abandoned jobs to failed state |
| `process_frame_pair_review_timeouts` | Every 1 hour | Send reminder notifications and fail overdue frame-pair reviews |
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
    storage/
    workers/
  workers/
    tasks/
    beat/
  core/
  db/
    migrations/
  tests/
```

## Database Session Strategy

API requests and Celery workers use distinct session management strategies:

- API requests: async SQLAlchemy sessions via FastAPI `Depends`.
- Celery workers: synchronous SQLAlchemy sessions with explicit lifecycle management.
- Connection pool: separate pool sizes for API and worker pools.

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
- Workers write step results directly to PostgreSQL and MinIO; they do not call the API for routine step updates.
- Clip retiming and source-audio stripping are first-class worker steps, not implicit behavior hidden inside FFmpeg composition.

## Authorization Model

- Workspace-scoped roles: `admin`, `member`, `reviewer`, `viewer`
- Project-level ownership checks enforced in service layer
- Admin-only operational endpoints separated under `/admin/` prefix
- Role definitions and detailed permission rules documented in `12-authentication-and-identity.md`

## Operational Concerns

- Centralized structured logging with correlation IDs through all layers
- Correlation identifiers across HTTP requests, job executions, and provider calls
- Rate limiting middleware on API endpoints
- Background reconciliation jobs owned explicitly by Celery Beat as listed above
