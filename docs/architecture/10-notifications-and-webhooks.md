# Notifications And Webhooks

## Goals

- Alert users to meaningful workflow events without overwhelming them with noise.
- Provide reliable, trackable delivery across multiple channels.
- Support programmatic webhooks for advanced users and agency integrations from Phase 6 onward.
- Keep notification failures non-blocking.

## Notification Channels

| Channel | Available From | Description |
| --- | --- | --- |
| In-app notification center | Phase 1 | Persistent bell icon with unread count |
| Transactional email | Phase 1 | Account and workflow-critical events |
| SSE render event stream | Phase 3 | Real-time render progress in the active browser session |
| Workspace webhook | Phase 6 | HTTP POST to a user-configured endpoint |

## Notification Event Catalog

### Phase 1 Events

| Event | In-App | Email | Trigger |
| --- | --- | --- | --- |
| `workspace.member_invited` | Yes | Yes | A user is invited to a workspace |
| `workspace.member_joined` | Yes | No | Workspace owner sees a member accept |
| `generation.ideas_ready` | Yes | No | Idea generation job completes |
| `generation.script_ready` | Yes | No | Script generation job completes |
| `generation.failed` | Yes | Yes | Any planning generation job fails permanently |

### Phase 3 Events

| Event | In-App | Email | SSE | Trigger |
| --- | --- | --- | --- | --- |
| `render.started` | Yes | No | Yes | Render job created and queued |
| `render.step.completed` | No | No | Yes | Individual render step succeeds |
| `render.step.failed` | Yes | No | Yes | Individual render step fails |
| `render.paused_for_frame_pair_review` | Yes | No | Yes | All scene frame pairs generated and awaiting review |
| `render.frame_pair_review_reminder` | Yes | Yes | No | 24h and 48h before frame-pair review timeout |
| `render.moderation_blocked` | Yes | No | Yes | A scene step blocked by output moderation |
| `render.completed` | Yes | Yes | Yes | All steps complete, export ready |
| `render.failed` | Yes | Yes | Yes | Render reaches terminal failure |
| `export.ready` | Yes | Yes | Yes | Export download link available |

### Phase 6 Events

| Event | In-App | Email | Webhook | Trigger |
| --- | --- | --- | --- | --- |
| `review.requested` | Yes | Yes | Yes | Scene plan or export submitted for review |
| `review.approved` | Yes | Yes | Yes | Reviewer approves a submission |
| `review.rejected` | Yes | Yes | Yes | Reviewer rejects a submission |
| `comment.added` | Yes | No | Yes | A comment is added to a project artifact |
| `member.role_changed` | Yes | Yes | No | A workspace member's role is updated |

## Data Model

`notification_events`, `webhook_deliveries`, and `notification_preferences` remain the persistence backbone for delivery tracking.

## Email Delivery

- Email is sent through an abstract `EmailProvider` interface.
- Email failures are logged and must not block any upstream workflow state transition.
- All emails include an unsubscribe link for non-critical notification types.

## Webhook Delivery

- Webhooks use HTTPS POST with a JSON payload and an HMAC-SHA256 signature header.
- Retry policy: up to 5 attempts with exponential backoff.
- After 5 failed attempts, the delivery status is set to `exhausted` and the workspace owner is notified via in-app notification.

## Notification Preferences

- Users can toggle email notifications per event category in their account settings.
- In-app notifications for critical events are not suppressible.
- Workspace owners can configure which event types trigger webhook deliveries.

## Implementation Phasing

| Phase | Work |
| --- | --- |
| Phase 1 | In-app notification center, email for invites and planning failures |
| Phase 3 | SSE stream with render, frame-pair review, moderation block, and export notifications |
| Phase 4 | Permanent render-failure notifications and operational alerts |
| Phase 6 | Webhook delivery system and review workflow notifications |
