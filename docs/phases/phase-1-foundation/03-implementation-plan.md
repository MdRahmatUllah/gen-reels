# Phase 1 Implementation Plan

## Backend Work

- Set up FastAPI application structure, config loading, auth middleware, and role checks.
- Define SQLAlchemy models and Alembic migrations for users, workspaces, projects, briefs, idea sets, and script-related tables.
- Build project, brief, idea generation, idea selection, and script generation services.
- Add session table, token refresh flow, and workspace switching support.
- Integrate input moderation checks before text generation dispatch.
- Add the first text provider adapter with normalized provider run records.
- Implement Celery tasks for idea and script generation.
- Add API rate limiting middleware and auth endpoint lockout rules.

## Frontend Work

- Set up React, routing, query client, UI shell, and auth state.
- Build dashboard and project creation flow.
- Create brief editor, idea selection surface, and script workspace.
- Add auth refresh and workspace switching behavior.
- Add generation status and reload-safe project views.

## Infra Work

- Stand up PostgreSQL, Redis, MinIO, and object-storage-compatible local services in Docker Compose.
- Add environment configuration and secret-loading strategy.
- Add CI for linting, tests, and basic build verification.

## QA Work

- Test project creation and brief persistence.
- Test idea generation and idea selection happy path.
- Test script generation from the selected idea.
- Test duplicate submission behavior and worker failure visibility.
- Test session expiry and unauthorized access paths.
- Test moderation rejection on blocked input.

## Acceptance Criteria

- The creator can start and resume multiple projects.
- Generated text outputs are versioned and recoverable.
- One selected idea is stored as the active concept for script generation.
- Unsafe inputs are stopped before generation providers are called.
