# Phase 1 Overview: Foundation

## Objective

Establish the product skeleton, workspace model, project lifecycle, and the first useful creator workflow: brief intake, idea generation, and script generation.

## Why This Phase Exists

The render pipeline should not be the first thing built. The platform needs a stable project model, editable drafts, auth, and saved workflow state before media generation becomes safe or cost-effective.

## In Scope

- Authentication and session management
- Workspace and membership foundations
- Project creation and brief intake
- Idea generation and script generation
- Script draft saving and versioning
- Input moderation on briefs and generation-triggering text
- Baseline API rate limiting for auth and write-heavy routes
- Dashboard and project list
- Initial async job framework and worker setup
- Object storage and database bootstrap

## Out Of Scope

- Scene planning
- Asset generation
- Final export rendering
- Billing and credits
- Team approval workflows beyond basic ownership

## What Users Get

- A working web application with account access
- The ability to create a project from a brief
- AI-assisted idea generation
- AI-assisted script generation with editable drafts
- Saved work that can be resumed later

## Deliverables

- React app shell and authenticated routes
- FastAPI service with workspace, project, brief, and script endpoints
- PostgreSQL schema baseline
- Redis and Celery setup
- Object storage integration
- Input moderation adapter integration
- API rate limiting middleware
- Initial text provider adapter

## Exit Criteria

- A user can create a workspace and a project
- A user can save a brief and generate multiple idea candidates
- A user can generate, edit, save, and revisit script drafts
- Briefs and prompt-like inputs pass through platform moderation before generation
- All generation work runs asynchronously through the job system
