# API Surface And Endpoint Catalog

## API Versioning Policy

All routes are prefixed with `/api/v1/`.

## API Groups

### Authentication And Identity

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/session`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/auth/workspace/select`

### Projects And Briefs

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/brief`
- `PATCH /api/v1/projects/{project_id}/brief`

### Ideas, Scripts, And Scene Planning

- `POST /api/v1/projects/{project_id}/ideas:generate`
- `GET /api/v1/projects/{project_id}/ideas`
- `POST /api/v1/projects/{project_id}/ideas/{idea_id}:select`
- `POST /api/v1/projects/{project_id}/scripts:generate`
- `GET /api/v1/projects/{project_id}/scripts`
- `PATCH /api/v1/projects/{project_id}/scripts/{script_version_id}`
- `POST /api/v1/projects/{project_id}/scripts/{script_version_id}:approve`
- `POST /api/v1/projects/{project_id}/scene-plan:generate`
- `POST /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:generate-prompt-pairs`
- `GET /api/v1/projects/{project_id}/scene-plans`
- `GET /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}`
- `PATCH /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}`
- `POST /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:approve`

### Presets

- `GET /api/v1/presets/visual`
- `POST /api/v1/presets/visual`
- `PATCH /api/v1/presets/visual/{preset_id}`
- `GET /api/v1/presets/voice`
- `POST /api/v1/presets/voice`
- `PATCH /api/v1/presets/voice/{preset_id}`

### Render Jobs And Assets

- `POST /api/v1/projects/{project_id}/renders`
- `GET /api/v1/renders/{render_job_id}`
- `POST /api/v1/renders/{render_job_id}:cancel`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:retry`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:approve-frame-pair`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:regenerate-frame-pair`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:replace-frame`
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
- `PATCH /api/v1/notification-preferences`

### Moderation And Admin

- `POST /api/v1/projects/{project_id}/moderation-reports`
- `GET /api/v1/admin/moderation`
- `POST /api/v1/admin/moderation/{moderation_event_id}:release`
- `POST /api/v1/admin/moderation/{moderation_event_id}:reject`
- `GET /api/v1/admin/renders`
- `GET /api/v1/admin/renders/{render_job_id}`
- `POST /api/v1/admin/renders/{render_job_id}:replay`

### Webhooks And API Keys

- `GET /api/v1/webhooks`
- `POST /api/v1/webhooks`
- `DELETE /api/v1/webhooks/{webhook_id}`
- `GET /api/v1/workspaces/{workspace_id}/api-keys`
- `POST /api/v1/workspaces/{workspace_id}/api-keys`
- `DELETE /api/v1/workspaces/{workspace_id}/api-keys/{api_key_id}`

### Local Worker Endpoints

- `POST /api/v1/workers/register`
- `POST /api/v1/workers/{worker_id}/heartbeat`
- `GET /api/v1/workers/{worker_id}/jobs/next`
- `POST /api/v1/workers/{worker_id}/jobs/{step_id}/result`

### Events

- `GET /api/v1/renders/{render_job_id}/events`

## Event Stream Types

- `render.created`
- `render.step.started`
- `render.step.completed`
- `render.step.failed`
- `render.paused_for_frame_pair_review`
- `render.completed`
- `render.cancelled`
- `render.failed`
- `usage.updated`
