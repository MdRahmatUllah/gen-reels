# Phase 4 Implementation Plan

## Backend Work

- Add step checkpoint and replay logic to orchestration services.
- Implement usage ledger writes tied to provider runs and export events.
- Add billing integration service and subscription state handling.
- Build moderation event review and asset release or rejection flows.
- Add cost accounting for frame-pair image generation and chained-scene invalidation reruns.

## Frontend Work

- Build usage dashboard and billing summary pages.
- Extend render history and failure views with richer diagnostics.
- Add moderation review surfaces for operators.

## Infra Work

- Add alerting for queue growth, provider instability, unusual cost spikes, and unexpected image-cost growth.
- Add dashboards for completion rate, retry rate, and cost per export.

## QA Work

- Test retry after provider timeout.
- Test resume from partial render completion.
- Test duplicate usage write protection.
- Test billing edge cases such as failed payment or insufficient credits.
