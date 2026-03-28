# Frontend design specification

**Purpose:** Single design document for the React application: information architecture, screens, and end-to-end user flows aligned with `docs/`, the canonical media pipeline in `docs/architecture/01-system-context.md`, and consolidated gaps from `a-project-documentation-review.md`, `b-project-documentation-review.md`, and `c-project-documentation-review.md`.

**Audience:** Product designers, frontend engineers, and API consumers defining UI contracts.

---

## 1. Sources and design constraints

### 1.1 Primary `docs/` inputs

| Document | What the frontend inherits |
| --- | --- |
| `architecture/02-react-frontend-architecture.md` | Stack (React, TS, Vite, Router, TanStack Query, Zustand, Zod, Tailwind), route map, SSE/polling, UI principles |
| `architecture/01-system-context.md` | Canonical workflow: brief → ideas → selected idea → script → 5–8 s scenes → start/end prompt pairs → chained frame pairs → first/last-frame video → strip/retime → narration → composition |
| `architecture/12-authentication-and-identity.md` | HttpOnly cookies, workspace-scoped JWT claims, roles (`admin`, `member`, `reviewer`, `viewer`) |
| `architecture/07-deployment-observability-and-security.md` | Signed URLs for assets; short TTL refresh pattern |
| `appendices/01-api-surface-and-endpoint-catalog.md` | Endpoint catalog; SSE event types |
| Phase overviews (`docs/phases/*`) | Phase-gated features (billing, templates, collaboration, admin) |

### 1.2 Consolidated review themes (a / b / c)

These are **product and API expectations** the UI must support even where backend docs still say “keyframe” only:

- **Idea selection:** Browse generated ideas, pick one **active** concept before script generation (`:select` style action).
- **Duration:** Target **60–120 s** master scripts and **5–8 s** segments (reviews note tension with some video APIs that prefer 4/6/8 s; UI should show provider-aware hints when known).
- **Prompt pairs:** Each scene has **`start_image_prompt`** and **`end_image_prompt`** editable in planning.
- **Frame pairs + chain:** Review **start + end** stills per scene; show **continuity anchor** (previous scene’s approved end frame). Changing scene *N* may invalidate downstream chained steps—surface this in the render monitor.
- **Post-video normalization:** Steps for **source audio policy** (silent request vs strip) and **clip retiming** (bounded speed, then pad/trim). Users need visibility, not necessarily manual control in MVP.
- **Single-scene preview:** Full pipeline on one segment before full render (`mode=preview`).

The UI should be built so **copy and layout** refer to **frame pairs** and **continuity**, while still working if the API temporarily exposes single-keyframe naming (map in the client or feature-flag).

---

## 2. Technical foundation

### 2.1 Stack (non-negotiable from architecture doc)

- **React 18+** with **TypeScript**
- **Vite** build
- **React Router** for routing
- **TanStack Query** for all server-authoritative data
- **Zustand** only for ephemeral UI (wizard step, filters, local editor chrome)
- **Zod** for forms and mutation payloads
- **Tailwind CSS** + shared component library

### 2.2 Realtime and polling

- Subscribe to **`GET /api/v1/renders/{render_job_id}/events`** (SSE).
- Implement reconnect with **`Last-Event-ID`**, backoff **2s → 4s → 8s → 16s → cap 30s**.
- After **3** failed reconnects, poll **`GET /api/v1/renders/{render_job_id}`** every **5 s** until SSE works again.
- If no SSE event for **30 s** while job should run, trigger a poll once.
- Listen for: `render.created`, `render.step.*`, `render.paused_for_keyframe_review` (treat as **frame-pair review** in UI copy when pairs are enabled), `render.completed`, `render.failed`, `render.cancelled`, `usage.updated`.

### 2.3 Asset display

- Never embed long-lived storage URLs. Call **`POST /api/v1/assets/{asset_id}/signed-url`** when rendering thumbnails, previews, or download links; on **403/expired**, re-request signed URL.

### 2.4 Auth transport

- Rely on **HttpOnly cookies** for access/refresh; use **`credentials: 'include'`** on `fetch`/API client.
- On **401** with token expiry hint, call refresh flow then retry queued requests (TanStack Query pattern).

---

## 3. Information architecture and routes

### 3.1 Public / auth routes

| Route | Screen |
| --- | --- |
| `/login` | Login |
| `/signup` | Registration (if product includes self-serve signup) |
| `/password-reset/request` | Request reset email |
| `/password-reset/confirm` | Set new password from token |

### 3.2 Authenticated app shell (`/app`)

All routes below assume workspace context in the JWT (active workspace from switcher).

| Route | Screen / area |
| --- | --- |
| `/app` | Redirect to dashboard or last project |
| `/app/workspaces` | Workspace list / create (optional if always forced through onboarding) |
| `/app/projects` | Project list (dashboard) |
| `/app/projects/new` | New project wizard entry |
| `/app/projects/:projectId/brief` | Brief intake |
| `/app/projects/:projectId/ideas` | Idea generation and **selection** |
| `/app/projects/:projectId/script` | Script workspace |
| `/app/projects/:projectId/scenes` | Scene plan + **prompt pairs** |
| `/app/projects/:projectId/renders` | Render jobs list + **render monitor** |
| `/app/projects/:projectId/renders/:renderJobId` | Render detail (steps, SSE, frame-pair review) |
| `/app/projects/:projectId/exports` | Export library |
| `/app/presets` | Visual + voice preset library |
| `/app/templates` | Project templates (Phase 5+) |
| `/app/settings` | User + workspace settings |
| `/app/settings/members` | Members (Phase 1 minimal; Phase 6 expanded roles) |
| `/app/billing` | Plans, usage, checkout (Phase 4+) |
| `/app/notifications` | Notification center (optional dedicated page; may be drawer only) |

### 3.3 Admin (`/admin`)

Role: platform **`admin`** (system role), not workspace admin.

| Route | Screen |
| --- | --- |
| `/admin` | Admin home |
| `/admin/queue` | Queue health / dead letters |
| `/admin/renders` | Render inspection |
| `/admin/workspaces` | Workspace ops, credit patches |
| `/admin/moderation` | Moderation queue (Phase 4+) |

---

## 4. Global shell UX

### 4.1 Layout

- **Header:** logo, primary nav (Projects, Presets, Templates when enabled), **workspace switcher**, **render queue indicator** (in-progress jobs count / link), **notifications**, **usage/credits** (Phase 4: headers `X-Credits-*` surfaced in UI), user menu.
- **Main:** page content.
- **Toasts:** async job started, moderation blocks, export ready.

### 4.2 Workspace switcher flow

1. User opens switcher → list workspaces from `GET /api/v1/workspaces`.
2. Select workspace → `POST /api/v1/auth/workspace/select` → new access cookie → invalidate TanStack Query caches tied to workspace scope.

### 4.3 Render queue indicator

- Query active renders for current workspace (dedicated endpoint or filter from projects).
- Badge count for `queued` / `running` / `paused_for_keyframe_review` (label as “Needs review” when paused).
- Click → `/app/projects/:projectId/renders/:renderJobId` or list.

### 4.4 Role-based visibility

| Capability | `admin` | `member` | `reviewer` | `viewer` |
| --- | --- | --- | --- | --- |
| Create/edit projects, run generation | ✓ | ✓ | — | — |
| Approve scene plans / frame review | ✓ | ✓ | if assigned | — |
| Comment / review requests (Phase 6) | ✓ | ✓ | ✓ | — |
| View exports | ✓ | ✓ | ✓ | ✓ |
| Billing, members, webhooks | ✓ | — | — | — |

Enforce in router guards and hide destructive primary buttons for viewers.

---

## 5. Feature flows and screens (complete)

Each subsection lists **goal**, **entry**, **screen inventory**, **happy path**, **edge cases**, and **primary API** (from catalog; additions from reviews marked *planned*).

---

### 5.1 Authentication

**Goal:** Secure session with workspace context.

**Screens**

- **Login:** email/password, link to reset, error states (rate limit, invalid creds).
- **Password reset request / confirm.**

**Happy path**

1. User submits login → cookies set → redirect `/app/projects`.
2. Token refresh on 401 transparent to user where possible.

**Edge cases**

- Lockout messaging after failed attempts.
- Session revoked → force re-login.

**API:** `POST /auth/login`, `POST /auth/logout`, `GET /auth/session`, `POST /auth/refresh`, password reset endpoints.

---

### 5.2 Dashboard — project list

**Goal:** Resume work and create projects.

**Screen: `/app/projects`**

- Table or cards: project name, last updated, phase badge (Brief / Ideas / Script / Scenes / Render / Export), moderation warnings.
- **CTA:** New project.
- Empty state: explain pipeline in one line + CTA.

**Happy path**

1. Load `GET /api/v1/projects` with pagination.
2. Click project → deep link to **last completed step** or user preference (optional: store `last_route` client-side).

**Edge cases**

- Archived projects filter.
- Quarantine indicator from moderation.

**API:** `GET /api/v1/projects`, `POST /api/v1/projects`.

---

### 5.3 New project & brief

**Goal:** Capture structured brief; trigger moderation before generation.

**Screen: `/app/projects/new` → redirects to `.../brief`**

**Screen: `/app/projects/:projectId/brief`**

- Form fields aligned with `project_briefs`: topic, audience, tone, product/campaign, constraints.
- **Save draft** (PATCH project/brief).
- **Generate ideas** CTA → async; show job status inline or toast.

**Happy path**

1. Create project `POST /api/v1/projects`.
2. Save brief `POST/PATCH .../brief`.
3. User clicks **Generate ideas** → `POST .../ideas:generate` (or job enqueue) → navigate to **Ideas** when job completes or show progress.

**Edge cases**

- Moderation rejection on brief or generation input → show reason, allow edit.
- Rate limit → show retry after.

**API:** `POST/PATCH .../brief`, `POST .../ideas:generate`, moderation-related errors.

---

### 5.4 Ideas — viral candidates and selection

**Goal:** Present multiple ideas; user **selects one** as the active concept for scripting.

**Screen: `/app/projects/:projectId/ideas`**

- List/grid of idea cards: title, hook, bullet summary, optional “viral angle” tags (product copy).
- Actions per card: **Select as active**, expand detail, **regenerate set** (optional).
- Clear **selected** state (badge, pin to top).
- Primary CTA when selection exists: **Continue to script**.

**Happy path**

1. `GET .../ideas` after generation completes.
2. User clicks **Select** → *planned* `POST .../ideas/{idea_id}:select` (reviews a/b/c); until then, UI can PATCH project with `selected_idea_id` if API exposes it on project).
3. Navigate to script with selected idea context.

**Edge cases**

- No ideas yet → prompt generate.
- Changing selection after script exists → warn **script may be stale**; offer regenerate script or new script version.

**API:** `GET .../ideas`, *planned* `POST .../ideas/{idea_id}:select`, `POST .../ideas:generate`.

---

### 5.5 Script workspace

**Goal:** 60–120 s master script, draft vs approved, versioning.

**Screen: `/app/projects/:projectId/script`**

- Rich text or structured blocks; display **target duration** hint (60–120 s) and word-count / estimated read time.
- Toolbar: **Save draft**, **Generate** (from selected idea), **Approve script** (gates scene plan).
- Version history sidebar: `script_version_id`, timestamps, who approved.
- Moderation banner if blocked.

**Happy path**

1. Load `GET .../scripts` (list versions) + active draft.
2. Edit → `PATCH .../scripts/{script_version_id}`.
3. **Approve** → `POST .../scripts/{script_version_id}:approve` → unlock **Scenes**.

**Edge cases**

- Approve disabled until moderation OK.
- Re-approval creates new immutable render binding for *future* jobs only (explain in UI tooltip).

**API:** `POST .../scripts:generate`, `GET/PATCH .../scripts`, `POST .../:approve`.

---

### 5.6 Scene planning and prompt pairs

**Goal:** Segment script into **5–8 s** scenes; each scene has narration/snippet, **`start_image_prompt`**, **`end_image_prompt`**, optional visual notes; approve plan before render.

**Screen: `/app/projects/:projectId/scenes`**

- **Timeline** or ordered list: segment index, duration estimate, script excerpt.
- Per segment **accordion** or split panel:
  - Editable **segment text** (what VO will say).
  - **Start image prompt** / **End image prompt** fields (Zod validated, max lengths).
  - Optional: **continuity note** (“same outfit as prior end”).
- Workspace-level **visual preset** and **voice preset** pickers (links to `/app/presets`).
- Actions: **Generate scene plan** (`POST .../scene-plan:generate`), **Save**, **Approve plan**.
- Warnings: segment &lt; 5 s or &gt; 8 s; total duration vs target; *provider hint* if video model uses 4/6/8 s clips (from b-review).

**Happy path**

1. `POST .../scene-plan:generate` from approved script.
2. User edits segments and prompt pairs → `PATCH .../scene-plans/{id}` (payload includes prompt fields per segment).
3. **Approve** → `POST .../scene-plans/{id}:approve`.

**Edge cases**

- Regenerate plan overwrites draft → confirm dialog.
- Reviewer-only workspace: read-only plan until review approved (Phase 6).

**API:** `POST .../scene-plan:generate`, `GET/PATCH .../scene-plans/...`, `POST ...:approve`, *planned* `POST ...:generate-prompt-pairs` if split from main generate.

---

### 5.7 Preset library

**Goal:** Reuse visual and voice defaults across projects.

**Screen: `/app/presets`**

- Tabs: Visual / Voice.
- List + create/edit modal: style descriptor, negative prompts, voice id, pace, stability, etc. (mirror backend schema).

**Happy path**

CRUD via `GET/POST/PATCH/DELETE` preset endpoints.

**Edge cases**

- Deleting preset in use → show dependent projects count if API returns it.

**API:** `/api/v1/presets/visual`, `/api/v1/presets/voice`.

---

### 5.8 Start render — full vs preview

**Goal:** Create `render_job` bound to approved script + scene plan; optional **single-scene preview**.

**Screen:** Modal or page section from **Scenes** or **Renders** tab.

- Radio: **Full reel** vs **Preview one scene** (scene picker).
- Summary: scene count, estimated credits (Phase 4), consistency snapshot id (advanced collapsible).
- Confirm → job created.

**Happy path**

1. `POST /api/v1/projects/{project_id}/renders` with `mode=full|preview`, optional `scene_id`.
2. Redirect to **Render monitor** for new `render_job_id`.

**Edge cases**

- Block if plan not approved or moderation pending.
- Chained pipeline: warn **longer wall-clock** vs parallel (educational tooltip from reviews).

**API:** `POST .../renders`.

---

### 5.9 Render monitor and frame-pair review

**Goal:** Per-step visibility, SSE progress, **approve frame pairs** before video (when gate active), retries, chain invalidation messaging.

**Screen: `/app/projects/:projectId/renders/:renderJobId`**

**Sections**

1. **Header:** status (`queued`, `running`, `paused_for_keyframe_review`, `failed`, `completed`), timestamps, cancel.
2. **Step timeline:** ordered steps per scene — e.g. prompt snapshot → **start image** → **end image** → *optional review gate* → **video** → **strip audio** → **retime** → **narration** → (subtitles) → composition.
3. **Scene rows:** expandable; show provider, cost, duration, errors, **Retry** (`POST .../steps/{step_id}:retry`).
4. **Frame-pair review panel** (when paused):
   - Side-by-side **Start** | **End** images for current scene (signed URLs).
   - **Previous scene end** thumbnail as **continuity anchor** context.
   - Actions: **Approve pair** (*planned* `approve-frame-pair` or reuse approve-keyframe with semantics for both), **Regenerate start**, **Regenerate end**, **Regenerate pair**, **Upload replace** (if supported).
5. **Warnings:** “Scene 3 changed; scenes 4+ must regenerate” if backend emits dependency flags (UI should consume if present in API).

**Happy path**

1. Open detail `GET /api/v1/renders/{render_job_id}`.
2. Attach SSE stream; merge events into step state.
3. On pause → user reviews → approve → SSE continues.

**Edge cases**

- Timeout failure `keyframe_review_timeout` → explain and offer new job.
- Partial failure → retry smallest unit.
- Phase 4: show credits reserved/consumed from headers on poll.

**API:** `GET /renders/{id}`, `POST :cancel`, `POST .../steps/{id}:retry`, `POST .../steps/{id}:approve-keyframe` (evolve to frame-pair), regenerate/replace endpoints, `GET .../events` SSE.

---

### 5.10 Export library

**Goal:** List exports, preview, download, duplicate.

**Screen: `/app/projects/:projectId/exports`**

- List: thumbnail, created at, type (`full` | `preview`), duration, loudness/subtitle flags in metadata.
- Row actions: **Play preview** (video element + signed URL), **Download**, **Duplicate** (Phase 5+ workflows).

**Happy path**

1. `GET .../exports`.
2. Click download → request signed URL for export asset.

**Edge cases**

- Export without subtitles (non-blocking step failed) → badge “No captions”.

**API:** `GET .../exports`, `GET /exports/{id}`, `POST ...:duplicate`, signed URL for asset.

---

### 5.11 Notifications

**Goal:** In-app notification of render complete, failure, review needed.

**UI:** Header bell → drawer with list; mark read.

**API:** `GET /notifications`, `POST ...:read`, `POST ...:read-all`, preferences `GET/PATCH`.

---

### 5.12 Billing and usage (Phase 4)

**Screen: `/app/billing`**

- Current plan, **credits remaining**, usage history, upgrade CTA.
- Before render: confirm modal if insufficient credits.

**API:** `GET /usage`, `GET /billing/subscription`, `POST /billing/checkout`, `POST /billing/portal`.

---

### 5.13 Templates (Phase 5)

**Screen: `/app/templates`**

- List workspace templates; clone into new project `POST .../templates/{id}:clone`.
- Create template from existing project (if supported).

---

### 5.14 Asset library & prompt history (Phase 5)

**Screens** (may live under project or workspace)

- Browse prior **images**, **clips**, **exports** with filters; **reuse** into new scene (API-dependent).
- Lineage view: which consistency snapshot + prompts produced asset (power users).

---

### 5.15 Subtitle style & export polish (Phase 5)

- Controls in export settings or visual preset: font, position, safe area for 9:16.
- Preview subtitle burn-in on sample clip if feasible client-side (or server preview asset).

---

### 5.16 Collaboration (Phase 6)

**Screens / enhancements**

- **Members & roles:** invite, change role.
- **Review requests:** assign reviewer to scene plan or export; **approve/reject** `POST /reviews/{id}:approve`.
- **Comments:** thread on project entities `GET/POST .../comments`.
- **Brand kits:** workspace-level enforced colors/type (link from preset or project).
- **Webhooks & API keys:** settings pages for automation.

---

### 5.17 Admin consoles

**Screens**

- **Queue:** depth, oldest task age, worker pools (from metrics or admin API).
- **Renders:** search by job id, workspace; **replay** `POST /admin/renders/{id}:replay`.
- **Workspaces:** list, adjust credits `PATCH .../credits`.
- **Moderation:** queue, release/reject quarantine.

**Access:** strict role gate; separate layout without creator nav noise.

---

## 6. End-to-end creator journey (single narrative)

This is the **full flow** a solo creator experiences, merging `docs` + reviews.

1. **Sign up / log in** → land **Dashboard**.
2. **Create project** → complete **Brief** → **Generate ideas** (async).
3. Open **Ideas** → compare cards → **Select active idea**.
4. Open **Script** → generate or write **60–120 s** script → edit → **Approve script**.
5. Open **Scenes** → **Generate scene plan** → adjust segments to **5–8 s** → edit **start/end image prompts** per scene → attach **visual + voice presets** → **Approve scene plan**.
6. Optional: **Presets** tuned in parallel anytime.
7. **Start render** (full or **preview** one scene).
8. **Render monitor** watches SSE; at **frame-pair review**, inspect **start/end** + **prior end** anchor → approve or regenerate.
9. After per-scene video, backend **strips** provider audio and **retimes** clips to narration; user sees step statuses (and warnings if bounds exceeded).
10. **Composition** completes → **notification** → **Exports** → preview / download.
11. Phase 4+: **Billing** awareness; Phase 5+: **templates** and **reuse**; Phase 6+: **team review**.

---

## 7. UI copy and state vocabulary

| Internal / API term | User-facing label (recommended) |
| --- | --- |
| `paused_for_keyframe_review` | “Review scene images” or “Approve frames” |
| Start / end image | “Opening frame” / “Closing frame” (or “Frame A / Frame B”) |
| Continuity anchor | “Previous scene’s last frame (continuity)” |
| Source audio strip | “Removing clip soundtrack” |
| Clip retime | “Matching video speed to voiceover” |
| `dead_letter` | “Needs support — retry unavailable” |

---

## 8. TanStack Query conventions (recommended)

- **Query keys:** `['workspace', id]`, `['projects']`, `['project', projectId]`, `['ideas', projectId]`, `['scripts', projectId]`, `['scenePlans', projectId]`, `['render', renderJobId]`, `['exports', projectId]`.
- **Invalidation:** on approve actions, invalidate scene plan + render list; on render complete, invalidate exports.
- **Mutations:** optimistic updates only for draft text fields with rollback on failure.

---

## 9. Testing focus (from architecture doc)

- Unit: Zod schemas for brief, script, segment prompt pairs, render payloads.
- Component: idea selection, prompt-pair editors, step timeline, SSE hook.
- E2E: happy path brief → export; frame-pair regenerate; admin queue (role mock).

---

## 10. Open design dependencies (track with backend)

| Item | Note |
| --- | --- |
| `POST .../ideas/{id}:select` | Listed in a/b reviews; confirm path and body |
| Frame-pair approve/regenerate endpoints | May supersede single `approve-keyframe` |
| Dependency invalidation payload | UI needs structured flags for “downstream scenes stale” |
| Video duration vs segment length | Show tooltips when provider clip length ≠ planned segment |
| `generateAudio=false` vs strip step | Affects whether user sees “strip” as separate step |

---

## 11. Non-goals (frontend)

- Full nonlinear editor (timeline scrubbing, multi-track manual mix) — out of scope per project overview.
- Local worker registration UI — Phase 7; optional stub link in settings.

---

*This document is the frontend counterpart to platform docs; keep it updated when `01-system-context.md`, the API catalog, or phase scopes change.*
