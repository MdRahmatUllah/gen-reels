# Phase 3 Implementation Plan

## Backend Work

- Implement render orchestration service and render job creation.
- Add models, migrations, and services for steps, assets, provider runs, and exports.
- Build image, video, and narration provider adapters.
- Add consistency pack snapshot resolution to render job creation.
- Implement frame-pair review state transitions plus regenerate and replace actions.
- Integrate output moderation before frame pairs and clips become eligible for downstream steps.
- Implement source-audio stripping and clip retiming workers.
- Implement FFmpeg composition worker and export generation service.

## Frontend Work

- Add render start flow from approved scene plan.
- Build frame-pair review UI with approve and regenerate flows.
- Build render monitor with scene-level progress.
- Add asset preview and export download pages.
- Show actionable error and retry controls.

## Infra Work

- Add heavier worker queues for media generation, audio normalization, retiming, and composition.
- Define object storage layout for generated media and exports.
- Add provider cost and latency metrics to dashboards.

## QA Work

- Validate end-to-end render on staging with representative sample projects.
- Test frame-pair review and regeneration.
- Test moderation rejection on unsafe generated assets.
- Test source-audio stripping and clip retiming.
- Test partial scene failure and retry.

## Acceptance Criteria

- One approved scene plan can produce one complete export.
- Users can see progress and understand failures without engineering help.
- The system preserves enough metadata to reproduce or debug a render attempt.
