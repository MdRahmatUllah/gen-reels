# Phase 4 Architecture

## Components Added

- Usage and billing service
- Enhanced render step checkpointing
- Dead-letter or failed-step review tooling
- Moderation review queue and operator release or reject workflow
- Admin operations views
- Reconciliation jobs for usage and billing consistency
- User-facing notification service for permanent render failures

## Data Changes

- Add `credit_ledger_entries`, `subscriptions`, and operational metadata fields
- Extend `provider_runs` with normalized cost, currency, request identifiers, and continuity-mode metadata
- Extend `render_steps` with retry history and recovery source references
- Extend billing formulas to account for frame-pair image generation per scene

## API Surface Added

- `GET /api/v1/usage`
- `GET /api/v1/billing/subscription`
- `POST /api/v1/billing/checkout`
- `POST /api/v1/billing/portal`
- `GET /api/v1/admin/moderation`
- `GET /api/v1/admin/renders`

## Risk Controls

- Billing state must not depend on only one provider callback.
- Usage records must be idempotent and reconcilable.
- Recovery tooling should not allow invalid state transitions or duplicate charges.
- Frame-pair retries and downstream invalidations must not double-charge silently.
