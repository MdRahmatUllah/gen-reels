# Rate Limiting And Quota Enforcement

## Goals

- Protect platform economics by enforcing credit and usage limits before expensive generation begins.
- Prevent individual workspaces from monopolizing shared generation queue capacity.
- Degrade access gracefully when limits are hit.
- Make quotas transparent to users before they hit a limit.

## Two Distinct Enforcement Layers

### Layer 1 - API Rate Limiting

Controls how many HTTP requests a workspace or user can make to the API within a time window.

### Layer 2 - Credit And Usage Quota

Controls how much total generation work a workspace can submit based on their subscription plan.

## Layer 1 - API Rate Limiting

Rate limiting is enforced at the reverse proxy or API gateway layer for unauthenticated routes, and at the FastAPI middleware layer for authenticated routes.

## Layer 2 - Credit And Usage Quota

### Credit Model

- Every workspace holds a credit balance in the `credit_ledger_entries` table.
- Credits are consumed when generation steps complete successfully, not when jobs are enqueued.
- Phase 3 records estimated usage units and actual provider cost for render and preview jobs.
- Phase 4 reserves credits when a render job is created based on estimated cost.

### Credit Costs By Modality

Defaults:

| Operation | Credit Cost |
| --- | --- |
| Idea generation (per set) | 1 |
| Script generation | 2 |
| Scene plan generation | 1 |
| Frame-pair image generation (per scene) | 10 |
| Video generation (per scene) | 20 |
| Narration generation (per scene) | 3 |
| Music generation (per export) | 5 |
| FFmpeg composition (per export) | 2 |

### Plan-Based Quotas

Subscription plans impose monthly generation limits:

| Plan | Monthly Renders | Max Concurrent Renders | Max Scenes Per Render |
| --- | --- | --- | --- |
| Free | 3 | 1 | 16 |
| Creator | 30 | 3 | 24 |
| Pro | 200 | 10 | 48 |
| Studio | Unlimited | 30 | 120 |

The increased scene caps reflect 60-120 second renders with 5-8 second scenes.

## Graceful Degradation

When a workspace hits a quota limit:

- active render jobs that are already running continue to completion
- new render job creation is blocked with `HTTP 402` or `HTTP 429` depending on the limit type
- planning operations are not blocked by render quotas unless the workspace is also credit-exhausted

## Quota Visibility API

From Phase 4 onward, authenticated responses include quota and credit headers:

- `X-Credits-Remaining`
- `X-Credits-Reserved`
- `X-Quota-Renders-Used`
- `X-Quota-Renders-Limit`
- `X-Quota-Reset`

## Operator Controls

- Operators can manually adjust workspace credit balances via the admin API.
- Operators can override plan-level quota limits for specific workspaces.
- Operators can pause all generation for a specific workspace without blocking planning operations.

## Implementation Phasing

| Phase | Work |
| --- | --- |
| Phase 1 | API rate limiting middleware and Redis counter setup |
| Phase 3 | Estimated usage-unit recording and provider-cost capture for renders and previews |
| Phase 4 | Full credit ledger, plan-based quotas, operator tooling, usage headers |
| Phase 5 | Queue-level concurrency controls and unusual-credit-consumption alerting |
