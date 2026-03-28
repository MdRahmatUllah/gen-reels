# Phase 2 Implementation Plan

## Backend Work

- Build segmentation logic with estimated narration timing.
- Add scene planning service and background task.
- Implement prompt-pair generation and validation.
- Implement preset services and associated schemas.
- Add approval state transitions and validation rules.

## Frontend Work

- Build scene planning workspace with editable ordered scenes.
- Add start-frame and end-frame prompt editing flows.
- Add visual preset and voice preset creation flows.
- Show duration estimates and validation warnings.

## Infra Work

- Add storage conventions for prompt snapshots and planning artifacts if needed.
- Extend logs and metrics for scene generation success, prompt-pair edit rate, and approval latency.

## QA Work

- Validate duration estimation and scene ordering.
- Test prompt-pair generation and editing.
- Test preset creation, reuse, and deletion rules.
- Test invalid approval attempts on incomplete plans.

## Acceptance Criteria

- Users can generate a usable first scene plan from an approved script.
- Users can manually edit prompt pairs without losing structural validity.
- One approved scene plan can be selected as the immutable basis for a future render job.
