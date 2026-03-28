# Phase 3 Architecture

## Components Added

- Render orchestration service
- Render job and render step models
- Image generation adapter
- Video generation adapter
- Speech generation adapter
- Music step service
- Source-audio stripping worker
- Clip retiming worker
- Composition and export worker
- Consistency pack resolution and enforcement
- Frame-pair review gate
- Export library UI and render monitor

## Data Changes

- Promote `render_jobs` and `render_steps` to full render models
- Add `provider_runs`, `assets`, `asset_variants`, and `exports`
- Add start-frame and end-frame asset roles
- Add `has_audio_stream`, `source_audio_policy`, and `timing_alignment_strategy` metadata
- Add `voice_preset_id` snapshot to render jobs

## API Surface Added

- `POST /api/v1/projects/{project_id}/renders`
- `GET /api/v1/renders/{render_job_id}`
- `POST /api/v1/renders/{render_job_id}:cancel`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:retry`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:approve-frame-pair`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:regenerate-frame-pair`
- `GET /api/v1/projects/{project_id}/exports`
- `GET /api/v1/renders/{render_job_id}/events`

## Risk Controls

- Consistency pack must be fully resolved before any generation step dispatches.
- Generated frame pairs and video clips must pass output moderation before they move downstream.
- Store enough metadata to debug timing mismatches, provider failures, and export corruption.
