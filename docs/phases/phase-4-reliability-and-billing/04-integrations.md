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
- Observability integrations must capture job IDs, provider identifiers, and correlation IDs.
- Recovery operations must be auditable.
- Moderation review actions must preserve the original moderation record and operator decision history.

## Error Strategy

- Payment failures should degrade access gracefully rather than corrupting projects.
- Usage reconciliation should be replayable if external billing writes fail.
- Queue alerts should escalate before user-facing latency becomes unacceptable.
- Moderation release or rejection actions must be idempotent and operator-audited.

## Cost Notes

- This phase is where commercial viability becomes measurable.
- No provider expansion should happen before cost dashboards and reconciliation logic are trusted.
