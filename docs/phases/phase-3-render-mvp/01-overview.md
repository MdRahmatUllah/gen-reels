# Phase 3 Overview: Render MVP

## Objective

Ship the first end-to-end reel generation flow from approved scene plan to downloadable 9:16 export.

## Why This Phase Exists

This is the first phase where the product becomes a true generator rather than a planning assistant. It should focus on a narrow, controllable output rather than broad provider choice or studio-grade polish.

## In Scope

- Render job creation
- Image generation per scene (using consistency pack)
- Keyframe review gate (user approves generated images before video generation)
- Video generation per scene (image-to-video preferred when approved keyframe exists)
- Narration generation
- Music from curated royalty-free library (bundled track selection)
- Subtitle generation (non-blocking — export proceeds if subtitles fail)
- FFmpeg-based composition
- Export library and download flow
- **Single-scene preview render** — full pipeline on one selected scene before committing to a full render job

## Out Of Scope

- Generated AI music (Phase 5)
- Advanced fallback routing
- Credits and billing enforcement (Phase 4)
- Team approvals
- Full multi-format export

## What Users Get

- The first complete reel output from the platform
- A single-scene preview to validate visual quality before running a full render
- Keyframe review to approve generated images before consuming expensive video generation capacity
- Progress visibility while the render is running
- Scene-level failures that can be inspected and retried
- A download surface for final exports

## Deliverables

- Render job domain and orchestration
- Provider adapters for image, video, and narration
- Consistency pack enforcement in generation calls
- Keyframe review UI and gate
- Preview render mode
- Composition worker using FFmpeg
- Music step using curated track library
- Export records and asset viewer
- Render status UI

## Exit Criteria

- A user can generate a full vertical reel from an approved scene plan
- A user can run a single-scene preview before committing to a full render
- Visual consistency pack is captured in every generation call
- Failed steps are visible and individually retryable
- Export metadata and asset history are stored for review

