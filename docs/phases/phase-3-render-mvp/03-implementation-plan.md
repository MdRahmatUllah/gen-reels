# Phase 3 Implementation Plan

## Backend Work

- Implement render orchestration service and render job creation.
- Add models, migrations, and services for steps, assets, provider runs, and exports.
- Build image, video, and narration provider adapters.
- Add consistency pack snapshot resolution to render job creation.
- Implement keyframe review state transitions plus regenerate and replace actions.
- Add preview render mode and preview asset promotion logic.
- Integrate output moderation before keyframes and clips become eligible for downstream steps.
- Implement FFmpeg composition worker and export generation service.
- Add retry, cancel, and status APIs.

## Frontend Work

- Add render start flow from approved scene plan.
- Add preview render entry point from a selected scene.
- Build keyframe review UI with approve, regenerate, and replace flows.
- Build render monitor with scene-level progress.
- Add asset preview and export download pages.
- Show actionable error and retry controls.

## Infra Work

- Add heavier worker queues for media generation and composition.
- Define object storage layout for generated media and exports.
- Add provider cost and latency metrics to dashboards.

## QA Work

- Validate end-to-end render on staging with representative sample projects.
- Validate preview render reuse in a later full render.
- Test keyframe review, regenerate, and replace flows.
- Test moderation rejection on unsafe generated assets.
- Test partial scene failure and retry.
- Test cancel behavior and export download integrity.
- Test asset cleanup and re-render version visibility.

## Milestones

- Milestone 1: render job model and orchestration
- Milestone 2: provider adapters and scene asset generation
- Milestone 3: composition and export
- Milestone 4: UI hardening and failure handling

## Acceptance Criteria

- One approved scene plan can produce one complete export.
- One scene can be preview-rendered before a full render is triggered.
- Users can see progress and understand failures without engineering help.
- The system preserves enough metadata to reproduce or debug a render attempt.
