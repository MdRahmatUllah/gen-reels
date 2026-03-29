# Frontend Implementation Review

Date: 2026-03-29

## Executive Summary

The frontend is ambitious and already covers most of the product surface area in mock form, but it does **not yet fully implement the frontend described in `docs/architecture`**, and it is **not yet state of the art** from either an architecture or design-system perspective.

The strongest parts are:

- Broad workflow coverage across brief, ideas, script, scenes, renders, exports, billing, admin, BYO providers, and local workers
- A clear visual point of view instead of generic boilerplate
- Good use of React Router, TanStack Query, and lightweight Zustand state for UI-only concerns
- Several pages already reflect the actual backend concepts well, especially scenes, renders, billing, provider settings, and local worker settings

The biggest issues are:

- The frontend does not currently build
- The app is split across **two different mock data systems** with overlapping page implementations
- The docs-required auth/session/workspace/realtime/notification architecture is only partially implemented
- Tailwind adoption is incomplete and the styling layer is fragmented between Tailwind, a very large custom CSS file, and many inline styles
- There are no frontend tests and no lint/test scripts in `package.json`

## Evidence Snapshot

- `npm run build` fails in `frontend/`
- `0` frontend test files found under `frontend/src`
- `0` `EventSource` / `Last-Event-ID` usages found in `frontend/src`
- `117` inline style usages found in `frontend/src`
- `45` legacy CSS variable usages found with `var(--color-*)` / `var(--font-*)`
- `165` mock references found in `frontend/src`

## Priority Findings

### 1. Critical: the frontend does not currently compile

Current state:

- `npm run build` fails with TypeScript errors
- Errors include unused imports/types, and `import.meta.env` not being typed in `src/lib/config.ts`

Examples:

- `frontend/src/lib/config.ts`
- `frontend/src/routes/app-pages.tsx`
- `frontend/src/hooks/use-brandkits.ts`
- `frontend/src/hooks/use-scenes.ts`
- `frontend/src/lib/mock-service.ts`
- `frontend/src/features/settings/TeamSettingsPage.tsx`

Impact:

- This blocks production readiness immediately
- It also means the current frontend cannot be treated as a stable reference implementation of the docs

Recommendation:

1. Make `npm run build` green before any further UI expansion
2. Add `vite/client` typing via `frontend/src/vite-env.d.ts` or `types` in `tsconfig.app.json`
3. Remove unused imports/types and turn build success into a required CI gate

### 2. Critical: there are two competing frontend architectures and two mock backends

Current state:

- `frontend/src/routes/app-pages.tsx` uses `frontend/src/lib/mock-api.ts`
- Most hooks and newer feature pages use `frontend/src/lib/mock-service.ts`
- `frontend/src/components/ui.tsx` pulls shell data from `mock-service`
- Router composition mixes old route pages with new feature pages

Examples:

- `frontend/src/app/router.tsx`
- `frontend/src/routes/app-pages.tsx`
- `frontend/src/routes/admin-pages.tsx`
- `frontend/src/lib/mock-api.ts`
- `frontend/src/lib/mock-service.ts`

Impact:

- The app has no single source of truth for mocked server state
- Shell data, project data, preset data, render data, and settings can drift across pages
- This makes the frontend harder to evolve toward the live backend because there is no single adapter boundary

Recommendation:

1. Collapse `mock-api.ts` and `mock-service.ts` into one domain-shaped mock adapter
2. Move page ownership fully into `features/*`
3. Retire the duplicate route-page implementations once feature pages replace them

### 3. High: auth and workspace context do not match the documented frontend architecture

Docs expectation:

- `GET /auth/session` bootstraps shell state
- workspace switching calls `POST /auth/workspace/select`
- refresh/session behavior is part of the app shell

Current state:

- `frontend/src/lib/auth.tsx` is mock-only
- Auth context only stores `user`, `isAuthenticated`, and loading/error state
- Workspace switching is only a Zustand value change in `frontend/src/state/ui-store.ts`
- No refresh rotation or backend session bootstrap integration is present

Examples:

- `frontend/src/lib/auth.tsx`
- `frontend/src/state/ui-store.ts`
- `frontend/src/components/ui.tsx`

Impact:

- Workspace context is not server-authoritative
- Role-aware navigation and permission-aware page behavior cannot be trusted
- The shell does not reflect the backend auth/session model implemented on the API side

Recommendation:

1. Replace mock auth bootstrapping with a single session loader backed by `/api/v1/auth/session`
2. Move workspace switching from Zustand-only to `/api/v1/auth/workspace/select`
3. Extend auth context to carry user, workspaces, active workspace, and active role

### 4. High: render realtime architecture is not implemented as documented

Docs expectation:

- SSE-based render progress
- `Last-Event-ID` reconnect
- exponential backoff
- polling fallback after repeated SSE failures

Current state:

- `frontend/src/hooks/use-renders.ts` uses query polling only
- No `EventSource`
- No SSE reconnect logic
- No `Last-Event-ID`
- No no-event watchdog logic

Examples:

- `frontend/src/hooks/use-renders.ts`
- `frontend/src/features/renders/RendersPage.tsx`

Impact:

- The most important live product surface does not match the architecture docs
- The UI currently describes SSE in text, but does not actually implement it

Recommendation:

1. Introduce a `useRenderStream(renderJobId)` hook using `EventSource`
2. Implement sequence-aware resume support using the backend event model
3. Keep polling only as the docs-specified fallback path

### 5. High: notification center and notification preferences UI are missing

Docs expectation:

- Notification center in the shell
- notification preferences
- render/review/membership/moderation notifications

Current state:

- Shell only shows a notification count chip
- No notification list page, drawer, or center
- No preferences screen
- No UI for webhook event subscriptions

Examples:

- `frontend/src/components/ui.tsx`
- no `useNotifications` hook
- no notification route or page

Impact:

- The shell is missing one of the core architectural surfaces
- The frontend does not expose the backend notification features that now exist

Recommendation:

1. Add a notification drawer or `/app/notifications`
2. Add preferences management under settings
3. Add webhook event configuration under workspace settings

### 6. High: admin and role-gated access are incomplete

Docs expectation:

- Admin routes are system-admin only
- workspace roles shape page actions

Current state:

- `/admin/*` uses the same `ProtectedRoute` as normal app routes
- No explicit admin gate exists
- The creator shell includes an `Admin Queue` navigation item regardless of role
- Team roles are mostly presentational and mock-only

Examples:

- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/app/router.tsx`
- `frontend/src/components/ui.tsx`
- `frontend/src/features/settings/TeamSettingsPage.tsx`

Impact:

- Frontend route security and UX do not match the documented role model
- The app can present controls to users who should not see them

Recommendation:

1. Add `RequireAdmin` and workspace-role route guards
2. Make navigation role-aware
3. Use auth/session claims instead of hard-coded or presentational role assumptions

### 7. High: provider and local worker settings are misaligned with the current docs/backend

Current state:

- Provider settings still expose generic providers like `openai`, `stability`, `elevenlabs`, and `runway`
- Local worker page copy describes a WebSocket daemon model
- The docs/backend now use workspace-scoped provider credentials and an HTTP polling worker protocol

Examples:

- `frontend/src/features/settings/ProviderSettingsPage.tsx`
- `frontend/src/features/settings/LocalWorkersPage.tsx`

Impact:

- The UI contract is drifting from the implemented backend
- Users would be taught the wrong mental model for BYO credentials and local workers

Recommendation:

1. Align provider options to actual provider keys and modalities from backend/docs
2. Update local worker UX to match `/workers/*` registration, heartbeat, job polling, and result submission
3. Add auth configuration / SSO boundary settings UI since the backend now supports that boundary

### 8. Medium: Tailwind adoption is incomplete and the design layer is fragmented

Current state:

- Tailwind is installed and partially used
- `frontend/src/styles/index.css` is still a very large custom stylesheet
- Many components still rely on inline styles
- Several newer pages use Tailwind utilities while legacy pages use semantic CSS classes
- Legacy variables like `var(--color-ink-lighter)` and `var(--font-mono)` are still referenced, but they are not part of the current main token set

Examples:

- `frontend/src/styles/index.css`
- `frontend/src/components/ui.tsx`
- `frontend/src/components/CommentThread.tsx`
- `frontend/src/components/ConflictResolutionModal.tsx`
- `frontend/src/features/assets/AssetsPage.tsx`
- `frontend/src/features/settings/TeamSettingsPage.tsx`

Impact:

- The UI will not feel consistently designed across surfaces
- Styling debt will slow down every future frontend change
- Token drift increases the chance of broken or inconsistent visuals

Recommendation:

1. Decide on one styling direction: Tailwind-first with small shared primitives
2. Move token definitions into Tailwind theme extensions plus a small CSS token layer
3. Remove inline styles aggressively
4. Replace legacy variable names with the current token system

### 9. Medium: folder boundaries do not match the architecture doc cleanly

Docs expectation:

- Feature ownership under `features/*`

Current state:

- Dashboard, projects, brief, script, presets, and an old billing implementation live in `frontend/src/routes/app-pages.tsx`
- Admin has both `routes/admin-pages.tsx` and `features/admin/*`
- Some pages are modernized, others remain legacy

Impact:

- Ownership is unclear
- Refactors will be slower and riskier
- The codebase is harder to onboard into

Recommendation:

1. Move route-level page components into domain feature folders
2. Keep `routes/*` for route composition only
3. Delete duplicate page modules after migration

### 10. Medium: collaboration and review UX are only partially implemented

Current state:

- Comments exist
- Scene conflict resolution exists
- Review flows are not represented as first-class product surfaces
- No dedicated review request queue or review resolution experience is present
- No visible collaboration-mode branching for solo vs multi-member workspaces

Examples:

- `frontend/src/components/CommentThread.tsx`
- `frontend/src/components/ConflictResolutionModal.tsx`
- `frontend/src/features/scenes/ScenesPage.tsx`

Impact:

- The collaboration phase is represented in fragments, not as a coherent workflow
- The frontend does not yet reflect the backend review features now available

Recommendation:

1. Add review request surfaces to scene plans and exports
2. Add review inbox/queue UI
3. Hide collaboration-heavy UI for solo workspaces unless relevant

### 11. Medium: there is no frontend testing or linting safety net

Current state:

- No test files found
- `package.json` has no `test` script
- `package.json` has no `lint` script

Impact:

- Regressions will be common during ongoing Tailwind migration and live-backend integration

Recommendation:

1. Add Vitest + React Testing Library
2. Add ESLint
3. Start with tests for auth guard, render status widgets, scene editing/conflict flow, and admin gating

### 12. Low: project documentation inside `frontend/` is drifting from the real implementation

Current state:

- `frontend/README.md` still describes the app as “Vanilla CSS” and references `/app/settings`
- The current codebase is now partially Tailwind-based and splits settings into multiple nested routes

Impact:

- Frontend contributors can be onboarded into the wrong architecture

Recommendation:

1. Update `frontend/README.md`
2. Document the current mock/live adapter plan and Tailwind migration status

## Architecture Coverage Matrix

| Surface from `docs/architecture` | Current status | Notes |
| --- | --- | --- |
| Auth flow | Partial | Login shell exists, but session bootstrap/refresh/workspace-select are not implemented against backend contracts |
| Workspace selector | Partial | UI selector exists, but it only mutates Zustand state |
| Main navigation | Present | Good shell coverage, but role gating is incomplete |
| Notification center | Missing | Only a count chip exists |
| Render queue indicator | Partial | Queue counts are present, but not as a live operational center |
| Usage and credit summary | Partial | Visible in shell/billing, but not tied to backend session/quota headers |
| Dashboard | Present | Implemented, but lives in legacy route-page layer |
| Projects and brief | Present | Implemented, but still on legacy data/page layer |
| Idea generation workspace | Present | Good mock flow coverage |
| Script workspace | Present | Good mock flow coverage |
| Scene planning workspace | Present | One of the stronger surfaces |
| Prompt-pair workspace | Partial | Editing exists, but the architecture-grade continuity/review model is incomplete |
| Render monitor | Partial | Rich UI, but no true SSE implementation |
| Export library | Present | Mocked and visually solid |
| Workspace settings | Partial | Several settings pages exist, but notification/webhook/auth-config coverage is missing |
| Billing | Present | Exists, but still mock-only |
| Admin queue/workspaces/renders | Partial | Surfaces exist, but no admin-only gating |

## Design Review

### What is already working well

- The product has a clear creative/operations identity instead of looking like default SaaS scaffolding
- The page shell with a large content area and inspector rail is a strong fit for this product
- The render and scene planning pages communicate pipeline status better than most early-stage internal tools
- The newer Tailwind-based settings and billing pages are visually cleaner and easier to evolve than the legacy route pages

### Why it is not yet “state of the art”

- The visual language is not consistently applied across the full app
- The shell is missing higher-end interaction patterns expected from a modern creative tool:
  - actionable notification center
  - real realtime behavior
  - strong role-aware navigation
  - polished modal/dialog patterns
  - consistent loading, empty, error, and success states
- Tables, forms, modals, and comments still use mixed patterns and old token names
- Search in the top bar is read-only and presentational
- Tailwind is present, but the design system is not yet unified around it

### Design-system improvement areas

1. Standardize the shell:
   - workspace switcher
   - queue indicator
   - notification center
   - global search / command bar
2. Standardize states:
   - loading
   - empty
   - error
   - success
   - blocked/review
3. Replace inline-styled tables and ad hoc cards with reusable primitives
4. Bring dialogs onto one accessible pattern
5. Define a real Tailwind token layer and stop inventing one-off utility mixes page by page

## Recommended Fix Order

### Phase A: Stabilize the frontend

1. Fix the TypeScript build
2. Add `vite/client` typing
3. Add lint and test scripts
4. Remove unused imports and duplicate dead pages where possible

### Phase B: Unify the architecture

1. Merge `mock-api.ts` and `mock-service.ts`
2. Move all route pages into `features/*`
3. Keep `router.tsx` focused only on route composition

### Phase C: Align the shell to the real backend

1. Implement auth/session bootstrap from `/api/v1/auth/session`
2. Implement workspace switching via `/api/v1/auth/workspace/select`
3. Add admin-only and role-aware route guards
4. Add notification center and preferences UI

### Phase D: Implement the realtime/render contract

1. Add `useRenderStream` with `EventSource`
2. Implement reconnect + fallback per the architecture doc
3. Wire render event UI to the backend `render_events` model

### Phase E: Align settings with the current platform

1. Replace generic provider settings with actual provider-credential surfaces
2. Update local worker page to match the polling protocol
3. Add webhook management UI
4. Add auth configuration / SSO boundary UI

### Phase F: Finish the Tailwind migration correctly

1. Convert shared layout and form primitives first
2. Remove legacy `var(--color-*)` / `var(--font-*)` references
3. Shrink `src/styles/index.css` into a token layer plus a few base utilities
4. Eliminate inline style usage except for truly dynamic values

## Final Verdict

The frontend is **promising but not yet architecture-complete**.

If I had to summarize it in one sentence:

> The product flow is impressively broad for a mock-first frontend, but the codebase still needs a unification pass, a realtime/auth shell pass, and a Tailwind/design-system cleanup pass before it truly matches the architecture docs or feels state of the art.

