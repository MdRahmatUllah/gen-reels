# Phase 1 Integrations

## External Integrations

- Authentication provider or internal auth implementation
- Transactional email provider for invites or login flows
- Primary text generation provider
- Moderation provider for text classification

## Internal Platform Integrations

- PostgreSQL
- Redis
- MinIO-backed object storage
- Docker Compose for local development
- Logging and error tracking

## Contract Requirements

- Text generation adapter accepts a structured brief payload and returns normalized idea or script output plus provider metadata.
- Idea selection is stored as project state, not as a transient frontend-only flag.
- Moderation integration must classify briefs and prompt-like input before they reach the text provider.

## Error Strategy

- Retry transient text provider failures.
- Translate provider failures into user-friendly states like `temporary_failure` or `invalid_request`.
- Do not leave partially created project records in unusable states.
- Moderation rejections must return a stable policy error category.
