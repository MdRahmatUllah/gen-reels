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
- Idea generation and idea selection workspace
- Script workspace
- Scene planning and prompt-pair workspace
- Preset library
- Render monitor and frame-pair review
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
    ideas/
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

## Route Map

- `/login`
- `/app`
- `/app/projects`
- `/app/projects/:projectId/brief`
- `/app/projects/:projectId/ideas`
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
| --- | --- | --- |
| Server state | TanStack Query cache | Projects, ideas, scripts, scenes, prompt pairs, assets, jobs, exports, usage, presets |
| Ephemeral UI state | Zustand | Wizard step progress, selected variants, filter and sort state, editor mode, unsaved draft edits |
| Realtime state | TanStack Query + SSE subscription | Render step events, progress updates, retry availability, frame-pair review status |

## SSE And Polling Strategy

Render progress uses Server-Sent Events (SSE) for real-time updates.

### Reconnect Strategy

The frontend must:

1. Reconnect automatically with `Last-Event-ID`.
2. Back off at 2s, 4s, 8s, 16s, capped at 30s.
3. Switch to polling `GET /renders/{render_job_id}` every 5 seconds after 3 failed reconnect attempts.
4. Trigger a poll if no event arrives for 30 consecutive seconds while a render is expected to be progressing.
5. Stop polling once SSE resumes.

## UI Principles

- Every async operation should expose status, timestamps, and the next available action.
- Users should always know whether they are editing a draft, reviewing an approved version, or viewing a generated result.
- Retry actions should target the smallest unit possible, usually a scene or asset.
- Prompt-pair and frame-pair review should show continuity context, including the prior scene's approved end frame.
- The render monitor should make it obvious when a change to scene `N` invalidates downstream chained scenes.

## Component Boundaries

- Page components compose domain-specific containers.
- Domain containers own data fetching and mutations.
- Presentational components remain reusable and stateless where possible.
- Editors should use schema-driven forms and a shared validation layer.

## Key Workflow Surfaces

- Idea list with "select active idea" action
- Scene planning workspace with `start_image_prompt` and `end_image_prompt` per scene
- Frame-pair review surface with start frame, end frame, and continuity anchor preview
- Render monitor with per-scene step breakdown including source-audio stripping and clip retiming
- Export library with preview vs full export distinction

## Frontend Testing

- Unit tests for utility and validation logic
- Component tests for idea selection, prompt-pair editors, and job status widgets
- End-to-end tests for the creator happy path and retry flows
- End-to-end tests for admin queue visibility and role-gated access
