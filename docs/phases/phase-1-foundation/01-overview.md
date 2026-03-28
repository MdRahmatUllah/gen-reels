# Phase 1 Overview: Foundation

## Objective

Establish the product skeleton, workspace model, project lifecycle, and the first useful creator workflow: brief intake, viral-style idea generation, idea selection, and script generation.

## Why This Phase Exists

The render pipeline should not be the first thing built. The platform needs a stable project model, editable drafts, auth, selected-idea state, and saved workflow state before media generation becomes safe or cost-effective.

## In Scope

- Authentication and session management
- Workspace and membership foundations
- Project creation and brief intake
- Idea generation and idea selection
- Script generation targeting 60-120 second outputs
- Script draft saving and versioning
- Input moderation on briefs and generation-triggering text
- Baseline API rate limiting for auth and write-heavy routes
- Dashboard and project list
- Initial async job framework and worker setup
- PostgreSQL, Redis, MinIO, and Docker bootstrap

## Out Of Scope

- Scene planning
- Prompt-pair authoring
- Asset generation
- Final export rendering
- Billing and credits

## What Users Get

- A working web application with account access
- The ability to create a project from a brief
- AI-assisted idea generation
- Explicit selection of one idea as the active concept
- AI-assisted script generation with editable drafts
- Saved work that can be resumed later

## Exit Criteria

- A user can create a workspace and a project
- A user can save a brief and generate multiple idea candidates
- A user can select one idea and generate, edit, save, and revisit script drafts
- Briefs and prompt-like inputs pass through platform moderation before generation
- All generation work runs asynchronously through the job system
