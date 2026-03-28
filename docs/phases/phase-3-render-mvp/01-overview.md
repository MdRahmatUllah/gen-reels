# Phase 3 Overview: Render MVP

## Objective

Ship the first end-to-end reel generation flow from approved scene plan to downloadable 9:16 export.

## In Scope

- Render job creation
- Chained start-frame and end-frame generation per scene
- Frame-pair review gate before video generation
- Video generation per scene with start/end frames when supported
- Narration generation
- Source-audio stripping or silent-video normalization
- Clip retiming to narration duration
- Music from curated royalty-free library
- Subtitle generation
- FFmpeg-based composition
- Export library and download flow

## Out Of Scope

- Generated AI music
- Advanced fallback routing
- Credits and billing enforcement
- Team approvals

## What Users Get

- The first complete reel output from the platform
- Continuity-aware frame-pair generation before video generation
- Progress visibility while the render is running
- Scene-level failures that can be inspected and retried
- A download surface for final exports

## Exit Criteria

- A user can generate a full vertical reel from an approved scene plan
- Visual continuity pack and chain references are captured in every generation call
- Provider audio is stripped or ignored before final composition
- Failed steps are visible and individually retryable
