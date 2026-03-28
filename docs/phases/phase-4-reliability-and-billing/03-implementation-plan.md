# Phase 4 Implementation Plan

## Backend Work

- Add step checkpoint and replay logic to orchestration services.
- Implement usage ledger writes tied to provider runs and export events.
- Add billing integration service and subscription state handling.
- Build moderation event review and asset release or rejection flows.
- Build reconciliation jobs for provider usage versus billed usage.
- Add admin endpoints for queue and failure inspection.

## Frontend Work

- Build usage dashboard and billing summary pages.
- Extend render history and failure views with richer diagnostics.
- Add moderation review surfaces for operators.
- Add retry and resume affordances that reflect new backend guarantees.

## Infra Work

- Add alerting for queue growth, provider instability, and unusual cost spikes.
- Add dashboards for completion rate, retry rate, and cost per export.
- Configure dead-letter handling or equivalent operational workflow for unrecoverable jobs.

## QA Work

- Test retry after provider timeout.
- Test resume from partial render completion.
- Test duplicate usage write protection.
- Test billing edge cases such as failed payment or insufficient credits.
- Test operator release and rejection flows for quarantined assets.

## Milestones

- Milestone 1: provider run cost capture and usage ledger
- Milestone 2: resumable render logic
- Milestone 3: billing pages and subscription integration
- Milestone 4: admin tooling and operational hardening

## Acceptance Criteria

- A failed multi-scene render can recover without repeating all successful scenes.
- Finance-facing usage totals match technical provider run totals.
- Operators can identify failures and queue pressure quickly.
