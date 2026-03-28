# Phase 4 Integrations

## External Integrations

- Billing and payment provider
- Error tracking provider
- Metrics or observability provider
- Moderation provider data and operator review workflow

## Internal Platform Integrations

- Provider run data from generation workers
- PostgreSQL usage and subscription records
- Redis queue metrics
- Admin visibility into worker state
- Moderation event and quarantine records

## Contract Requirements

- Billing integration must support subscription state, payment status, and usage-triggered credit deduction.
- Usage reconciliation must understand frame-pair image generation as a distinct billable unit.
- Recovery operations must be auditable.
