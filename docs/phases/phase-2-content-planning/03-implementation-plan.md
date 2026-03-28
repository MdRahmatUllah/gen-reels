# Phase 2 Implementation Plan

## Backend Work

- Build segmentation logic with estimated narration timing.
- Add scene planning service and background task.
- Implement preset services and associated schemas.
- Add approval state transitions and validation rules.
- Extend provider run logging for planning tasks.

## Frontend Work

- Build scene planning workspace with editable ordered scenes.
- Add visual preset and voice preset creation flows.
- Show duration estimates and validation warnings.
- Add clear draft versus approved indicators.

## Infra Work

- Add storage conventions for prompt snapshots and planning artifacts if needed.
- Extend logs and metrics for scene generation success and edit rate.

## QA Work

- Validate duration estimation and scene ordering.
- Test editing and re-approval behavior.
- Test preset creation, reuse, and deletion rules.
- Test invalid approval attempts on incomplete plans.

## Milestones

- Milestone 1: segmentation and scene domain model
- Milestone 2: scene plan generation
- Milestone 3: presets and approval workflow
- Milestone 4: polish and readiness for render implementation

## Acceptance Criteria

- Users can generate a usable first scene plan from an approved script.
- Users can manually edit scenes without losing structural validity.
- One approved scene plan can be selected as the immutable basis for a future render job.

