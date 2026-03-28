# Phase 6 Integrations

## External Integrations

- Notification provider for invites and review alerts
- Optional SSO provider in later studio tiers
- Webhook consumer endpoints owned by customers

## Internal Platform Integrations

- Existing workspace, preset, and project models
- Audit event system
- Billing plan and permission enforcement

## Contract Requirements

- Notifications must be tied to review events and membership changes.
- SSO or enterprise identity should remain a separate integration boundary from core auth.
- Brand kit enforcement points must be explicit and testable.
- Workspace API keys must be hash-stored, role-scoped, and revocable.
- Webhook deliveries must be HMAC-signed and replay-safe.

## Error Strategy

- Permission failures must return precise, predictable reasons.
- Missing brand kit or review state should not break the core project flow.
- Notification failures must not block state transitions.

## Cost Notes

- Collaboration features should improve account expansion and retention rather than raw render volume.
- Studio features can justify higher plans once auditability and brand controls are stable.
