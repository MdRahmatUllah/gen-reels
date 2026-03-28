# Phase 1 Integrations

## External Integrations

- Authentication provider or internal auth implementation
- Transactional email provider for invites or login flows
- Primary text generation provider
- Moderation provider for text classification

## Internal Platform Integrations

- PostgreSQL
- Redis
- Object storage
- Logging and error tracking

## Contract Requirements

- Text generation adapter accepts a structured brief payload and returns normalized idea or script output plus provider metadata.
- Auth integration must expose workspace-aware identity and session information.
- Email integration should be abstract enough to replace later without touching project logic.
- Moderation integration must classify briefs and prompt-like input before they reach the text provider.

## Credential Handling

- Platform-level API keys live in secure secrets management.
- No BYO credentials yet.
- Keep provider credentials isolated from worker logs and user-visible error messages.

## Error Strategy

- Retry transient text provider failures.
- Translate provider failures into user-friendly states like `temporary_failure` or `invalid_request`.
- Do not leave partially created project records in unusable states.
- Moderation rejections must return a stable policy error category without exposing classifier internals.

## Cost Notes

- Text generation cost is low, so Phase 1 prioritizes velocity and reliability over provider routing sophistication.
- Capture cost metadata anyway so later usage tracking has historical continuity.
- Moderation checks are mandatory even though they add extra requests, because removing them would create policy and support risk immediately.
