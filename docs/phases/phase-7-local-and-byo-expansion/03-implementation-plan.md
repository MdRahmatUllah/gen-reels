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

## Infra Work

- Add secure secret storage and key rotation support.
- Add health monitoring for local worker availability and stale registrations.
- Add operational safeguards for invalid routing policies.

## QA Work

- Test credential rotation and revocation.
- Test worker registration, heartbeat expiry, and capability mismatch.
- Test routing fallback behavior and fail-closed cases.
- Test usage accounting across all execution modes.

## Milestones

- Milestone 1: BYO credential vault
- Milestone 2: local worker contract and registration
- Milestone 3: routing engine integration
- Milestone 4: visibility, billing, and hardening

## Acceptance Criteria

- Advanced users can route work safely without changing the main workflow.
- Invalid credentials or offline local workers do not silently corrupt jobs.
- Hosted and non-hosted usage remain measurable and supportable.

