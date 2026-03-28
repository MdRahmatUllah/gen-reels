# Phase 2 Architecture

## Components Added

- Segmentation and timing service
- Scene planning service
- Prompt-pair generation service
- Visual preset and voice preset services
- Consistency pack initialization service
- Approval status transitions for script and scene plan records
- Scene planning UI and preset management screens

## Duration Estimation

Scene duration estimation uses a two-tier approach:

1. Word-count heuristic by default
2. TTS timing override in later phases once narration dry runs are available

Timing warnings surface to users:

- warning if an estimated segment duration exceeds 8 seconds
- warning if total script duration falls outside 60-120 seconds

## Data Changes

- Add `scene_plans` and `scene_segments`
- Add `visual_presets` and `voice_presets`
- Add `start_image_prompt` and `end_image_prompt` fields on `scene_segments`
- Add approval timestamps and approval actor fields to scripts and scene plans

## API Surface Added

- Segment script endpoint
- Generate scene plan endpoint
- Generate prompt pairs endpoint
- Scene plan fetch and update
- Script approve endpoint
- Scene plan approve endpoint
- Preset CRUD endpoints

## Frontend Structure

- Scene timeline workspace
- Scene editor with duration estimate display
- Start-frame and end-frame prompt editors
- Visual preset picker
- Voice preset picker
- Approval action surfaces

## Risk Controls

- Manual edits must override generated scene suggestions cleanly.
- Approved records are immutable inputs to later renders.
- Timing estimates must be surfaced as advisory warnings, not blocking validation.
