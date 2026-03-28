# React Frontend Architecture

## Frontend Stack

- React with TypeScript
- Vite for the application build
- React Router for route composition
- TanStack Query for server state
- Zustand for lightweight client-side workflow state
- Zod for form and payload validation
- Tailwind CSS plus a shared component library for UI consistency

This stack keeps the frontend fast to build, straightforward to operate, and clearly separated from the FastAPI backend.

## Application Structure

### Core Shell

- Auth flow
- Workspace selector
- Main navigation
- Notification center
- Render queue indicator
- Usage and credit summary

### Main Product Areas

- Dashboard
- Project creation and brief intake
- Idea and script workspace
- Scene planning workspace
- Preset library
- Render monitor
- Export library
- Workspace settings and billing

## Suggested Frontend Folder Structure

```text
src/
  app/
  routes/
  features/
    auth/
    dashboard/
    projects/
    scripts/
    scenes/
    renders/
    exports/
    presets/
    billing/
    admin/
  components/
  hooks/
  lib/
  state/
  types/
```

- `app/` owns providers, routing bootstrap, and app shell wiring.
- `routes/` defines route modules and route-level loaders if used.
- `features/` groups domain behavior by product area.
- `components/` stores shared UI components that are not feature-specific.
- `hooks/` and `lib/` hold reusable client logic.
- `state/` holds lightweight client stores and UI-only state.
- `types/` holds frontend domain types and API-facing view models when not shared from a generated client.

## Route Map

- `/login`
- `/app`
- `/app/projects`
- `/app/projects/:projectId/brief`
- `/app/projects/:projectId/script`
- `/app/projects/:projectId/scenes`
- `/app/projects/:projectId/renders`
- `/app/projects/:projectId/exports`
- `/app/presets`
- `/app/templates`
- `/app/settings`
- `/app/billing`
- `/admin`
- `/admin/queue`
- `/admin/workspaces`
- `/admin/renders`

Admin routes are available only to users with the `admin` system role and are excluded from workspace-scoped navigation.

## State Ownership

### Rule: Zustand Holds Only Ephemeral UI State

Zustand is strictly limited to ephemeral client-side state. Do not store server-authoritative data in Zustand.

| State Type | Owner | Examples |
|---|---|---|
| Server state | TanStack Query cache | Projects, scripts, scenes, assets, jobs, exports, usage, presets |
| Ephemeral UI state | Zustand | Wizard step progress, selected variants, filter/sort state, editor UI mode, unsaved draft edits |
| Realtime state | TanStack Query + SSE subscription | Render step events, progress updates, retry availability |

**Rule:** Render status, job progress, and any approval state are **never** stored in Zustand. They live in the TanStack Query cache and are refreshed via the render event subscription or polling fallback. Divergence between Zustand and the server model is a bug, not a feature.

## SSE And Polling Strategy

Render progress uses Server-Sent Events (SSE) for real-time updates.

### Reconnect Strategy

SSE connections can drop due to proxy timeouts or network interruptions. The frontend must:

1. **Automatic reconnect:** Use the browser's built-in SSE reconnect with `Last-Event-ID`. On reconnect, the server replays events since the last received event (up to 50 events per render job).
2. **Backoff:** Reconnect attempts back off with intervals: 2s, 4s, 8s, 16s, capped at 30s.
3. **Polling fallback:** After 3 failed reconnect attempts, switch to polling `GET /renders/{render_job_id}` every 5 seconds.
4. **Stale detection:** If no SSE event arrives for 30 consecutive seconds and a render is expected to be progressing, trigger a poll to confirm status.
5. **Resumption:** Once SSE reconnects successfully, stop polling and resume event stream consumption.

### No Separate Polling Endpoint

The polling fallback uses the same `GET /renders/{render_job_id}` status endpoint. No special polling endpoint is needed. The response model is identical whether the data arrives via SSE or polling.

## UI Principles

- Every async operation should expose status, timestamps, and the next available action.
- Users should always know whether they are editing a draft, reviewing an approved version, or viewing a generated result.
- Retry actions should target the smallest unit possible, usually a scene or asset.
- Phase-gated features should already fit the final navigation model so the information architecture does not need a redesign later.

## Component Boundaries

- Page components compose domain-specific containers.
- Domain containers own data fetching and mutations.
- Presentational components remain reusable and stateless where possible.
- Editors should use schema-driven forms and a shared validation layer.

## Rendering Progress UX

- Use SSE for server-to-client progress updates with polling fallback as described above.
- Show high-level render status plus per-scene step progress.
- Preserve job history so users can inspect failures after a refresh.
- Expose retry, cancel, and duplicate render actions from the same UI surface.

## Frontend Testing

- Unit tests for utility and validation logic
- Component tests for editors and job status widgets
- End-to-end tests for the creator happy path and retry flows
- End-to-end tests for admin queue visibility and role-gated access


