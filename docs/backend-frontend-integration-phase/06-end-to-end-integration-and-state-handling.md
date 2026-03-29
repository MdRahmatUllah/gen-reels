# End-to-End Integration and State Handling

## Objective
- Define the current live runtime behavior across auth, creator workflow, render monitoring, collaboration, and settings, and identify what still needs cleanup.

## Shell State
- Backend session plus live project/workspace data are now the source of truth for the shell in [frontend/src/components/ui.tsx](f:/my-projects/reels-generation/frontend/src/components/ui.tsx).
- Zustand in [frontend/src/state/ui-store.ts](f:/my-projects/reels-generation/frontend/src/state/ui-store.ts) remains limited to ephemeral UI state.

## Async Planning Flow

### Ideas
- generate ideas starts a backend job
- the UI shows accepted/loading state
- the frontend refetches `["ideas", projectId]` until the latest set appears

### Scripts
- generate script starts a backend job
- the frontend refetches script data until the latest version is available

### Scene Plan
- generate scene plan starts a backend job
- the frontend refetches scene plan data until the active/latest plan is available
- scene edits still use backend-aware full-payload patch behavior where required

### Prompt Pairs
- prompt-pair generation is treated as an async job
- the frontend refetches scene plan detail until prompt data arrives

## Render State Strategy
- Project render list, render detail, render actions, and export data are now backend-backed.
- SSE remains the preferred backend render stream path, with polling/refetch kept as the safe client fallback.
- Render job ids are treated as the authoritative handle for cancel/retry/detail operations.

## Current Live Screen Coverage
- auth and login flow
- shell and workspace switcher
- projects, brief, ideas, scripts, scenes, renders, and exports
- provider settings and local workers
- brand kits
- scene comments
- template cloning

## Remaining Screen Work
- Admin queue/workspace pages still need contract alignment or scope reduction.
- Legacy routes still using `mock-api.ts` should be moved onto shared live adapters.
- The live path should stop depending on `mock-service.ts` wrappers where direct hook-to-live-api usage is practical.

## Optimistic Update Rules
- Safe optimistic behavior:
  - local loading spinners
  - disabled controls
  - pending banners
- Complex workflow objects such as scene plans and render steps should remain server-truth driven.

## Acceptance Criteria From Here
- Live mode shell, workflow, renders, exports, provider settings, brand kits, comments, and template cloning remain backend-backed.
- Remaining legacy/admin pages are either integrated or explicitly scoped out.
- No target live screen depends on accidental mock-only state.
