# Phase 1 Implementation Plan

## Backend Work

- Set up FastAPI application structure, config loading, auth middleware, and role checks.
- Define SQLAlchemy models and Alembic migrations for users, workspaces, projects, briefs, and script-related tables.
- Build project, brief, idea generation, and script generation services.
- Add session table, token refresh flow, and workspace switching support.
- Integrate input moderation checks before text generation dispatch.
- Add the first text provider adapter with normalized provider run records.
- Implement Celery tasks for idea and script generation.
- Add API rate limiting middleware and auth endpoint lockout rules.

## Frontend Work

- Set up React, routing, query client, UI shell, and auth state.
- Build dashboard and project creation flow.
- Create brief editor and script workspace.
- Add auth refresh and workspace switching behavior.
- Add generation status and reload-safe project views.

## Infra Work

- Stand up PostgreSQL, Redis, and object storage in local and staging environments.
- Add environment configuration and secret-loading strategy.
- Add CI for linting, tests, and basic build verification.

## QA Work

- Test project creation and brief persistence.
- Test idea and script generation happy path.
- Test duplicate submission behavior and worker failure visibility.
- Test session expiry and unauthorized access paths.
- Test moderation rejection on blocked input.
- Test auth and write-route rate limiting behavior.

## Milestones

- Milestone 1: skeleton app, auth, workspace model
- Milestone 2: projects and briefs
- Milestone 3: idea and script generation
- Milestone 4: hardening, tests, and handoff to Phase 2

## Acceptance Criteria

- The creator can start and resume multiple projects.
- Generated text outputs are versioned and recoverable.
- System logs and provider metadata exist for each generation request.
- Unsafe inputs are stopped before generation providers are called.
