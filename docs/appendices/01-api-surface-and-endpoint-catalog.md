# API Surface And Endpoint Catalog

## API Versioning Policy

All routes are prefixed with `/api/v1/`. This prefix is mandatory from the first production deployment.

**Version bump policy:**
- Minor additions (new optional fields, new endpoints) are non-breaking and do not require a version bump.
- Breaking changes (removed fields, changed required fields, altered response shapes, removed endpoints) require a new major version prefix (e.g., `/api/v2/`).
- When a new version is released, the previous version remains active for a minimum 90-day deprecation window with a `Deprecation` header on all responses.

## API Groups

### Authentication And Identity

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/session`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/auth/workspace/select`

### Workspaces And Membership

- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}`
- `PATCH /api/v1/workspaces/{workspace_id}`
- `POST /api/v1/workspaces/{workspace_id}/members`
- `PATCH /api/v1/workspaces/{workspace_id}/members/{user_id}`
- `DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}`
- `GET /api/v1/workspaces/{workspace_id}/usage`

### Projects And Briefs

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}` — soft delete / archive
- `POST /api/v1/projects/{project_id}/brief`
- `PATCH /api/v1/projects/{project_id}/brief`

### Ideas, Scripts, And Scene Planning

- `POST /api/v1/projects/{project_id}/ideas:generate`
- `GET /api/v1/projects/{project_id}/ideas`
- `POST /api/v1/projects/{project_id}/scripts:generate`
- `GET /api/v1/projects/{project_id}/scripts`
- `PATCH /api/v1/projects/{project_id}/scripts/{script_version_id}`
- `POST /api/v1/projects/{project_id}/scripts/{script_version_id}:approve`
- `POST /api/v1/projects/{project_id}/scene-plan:generate`
- `GET /api/v1/projects/{project_id}/scene-plans`
- `GET /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}`
- `PATCH /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}`
- `POST /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:approve`

### Presets And Brand Assets

- `GET /api/v1/presets/visual`
- `POST /api/v1/presets/visual`
- `PATCH /api/v1/presets/visual/{preset_id}`
- `DELETE /api/v1/presets/visual/{preset_id}`
- `GET /api/v1/presets/voice`
- `POST /api/v1/presets/voice`
- `PATCH /api/v1/presets/voice/{preset_id}`
- `DELETE /api/v1/presets/voice/{preset_id}`
- `GET /api/v1/brand-kits`
- `POST /api/v1/brand-kits`
- `PATCH /api/v1/brand-kits/{brand_kit_id}`

### Templates (Phase 5)

- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`
- `DELETE /api/v1/templates/{template_id}`
- `POST /api/v1/templates/{template_id}:clone` — clone template into a new project

### Render Jobs And Assets

- `POST /api/v1/projects/{project_id}/renders` — supports `mode=full|preview` and optional `scene_id` for preview mode
- `GET /api/v1/renders/{render_job_id}`
- `POST /api/v1/renders/{render_job_id}:cancel`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:retry`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:approve-keyframe`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:regenerate-keyframe`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:replace-keyframe`
- `GET /api/v1/projects/{project_id}/assets`
- `POST /api/v1/assets/{asset_id}/signed-url`

### Exports

- `GET /api/v1/projects/{project_id}/exports`
- `GET /api/v1/exports/{export_id}`
- `POST /api/v1/exports/{export_id}:duplicate`

### Billing And Usage

- `GET /api/v1/usage`
- `GET /api/v1/billing/subscription`
- `POST /api/v1/billing/checkout`
- `POST /api/v1/billing/portal`

### Notifications

- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{notification_id}:read`
- `POST /api/v1/notifications:read-all`
- `GET /api/v1/notification-preferences`
- `PATCH /api/v1/notification-preferences`

### Moderation

- `POST /api/v1/projects/{project_id}/moderation-reports`
- `GET /api/v1/admin/moderation`
- `POST /api/v1/admin/moderation/{moderation_event_id}:release`
- `POST /api/v1/admin/moderation/{moderation_event_id}:reject`

### Webhooks (Phase 6)

- `GET /api/v1/webhooks`
- `POST /api/v1/webhooks`
- `DELETE /api/v1/webhooks/{webhook_id}`

### API Keys (Phase 6)

- `GET /api/v1/workspaces/{workspace_id}/api-keys`
- `POST /api/v1/workspaces/{workspace_id}/api-keys`
- `DELETE /api/v1/workspaces/{workspace_id}/api-keys/{api_key_id}`

### Reviews And Comments (Phase 6)

- `POST /api/v1/projects/{project_id}/reviews`
- `POST /api/v1/reviews/{review_id}:approve`
- `POST /api/v1/reviews/{review_id}:reject`
- `GET /api/v1/projects/{project_id}/comments`
- `POST /api/v1/projects/{project_id}/comments`

### Admin Routes (role-gated)

- `GET /api/v1/admin/renders`
- `GET /api/v1/admin/renders/{render_job_id}`
- `POST /api/v1/admin/renders/{render_job_id}:replay`
- `GET /api/v1/admin/workspaces`
- `PATCH /api/v1/admin/workspaces/{workspace_id}/credits`
- `GET /api/v1/admin/queue`
- `DELETE /api/v1/admin/users/{user_id}/sessions` — revoke all sessions for a user (Phase 3)
- `GET /api/v1/admin/workers` (Phase 7)
- `DELETE /api/v1/admin/workers/{worker_id}` (Phase 7)

### Local Worker Endpoints (Phase 7 — stub from Phase 3)

- `POST /api/v1/workers/register`
- `POST /api/v1/workers/{worker_id}/heartbeat`
- `GET /api/v1/workers/{worker_id}/jobs/next`
- `POST /api/v1/workers/{worker_id}/jobs/{step_id}/result`

### Events

- `GET /api/v1/renders/{render_job_id}/events` — SSE stream

## Response Design

- Return stable IDs and version IDs for all mutable workflow records.
- Return job references for async operations.
- Expose machine-readable status enums plus user-display messages.
- Include pagination on list endpoints from the beginning.
- From Phase 4 onward, authenticated responses include quota and credit headers: `X-Credits-Remaining`, `X-Credits-Reserved`, `X-Quota-Renders-Used`, `X-Quota-Renders-Limit`, `X-Quota-Reset`.

## Event Stream Types

- `render.created`
- `render.step.started`
- `render.step.completed`
- `render.step.failed`
- `render.paused_for_keyframe_review`
- `render.completed`
- `render.cancelled`
- `render.failed`
- `usage.updated`

