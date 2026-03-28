# Phase 7 Implementation Plan

## Backend Work

- Build encrypted storage and lifecycle management for BYO credentials.
- Implement local worker registration, health check, and capability endpoints.
- Add routing policy service and integrate it into orchestration.
- Extend usage ledger and provider runs with execution mode distinctions.

## Frontend Work

- Build workspace provider settings and execution mode controls.
- Add local worker monitoring views.
- Extend usage and billing pages to reflect hosted, BYO, and local execution.

## QA Work

- Test credential rotation and revocation.
- Test worker registration, heartbeat expiry, ordered-reference capability mismatch, and first/last-frame routing.
- Test routing fallback behavior and fail-closed cases.
