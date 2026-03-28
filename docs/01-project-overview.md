# Project Overview

## Vision

Build a platform that converts a user brief into a publish-ready short-form vertical video by orchestrating idea generation, idea selection, script creation, scene planning, paired visual frame generation, narration, background music, and final media assembly.

The product should feel like a reliable production workflow rather than a prompt playground. The long-term moat is not a single model provider. It is a predictable, resumable, editable system that produces usable content with good defaults, reusable presets, continuity controls, and cost control.

## Primary Users

### 1. Faceless Content Creators

- Need fast production of vertical reels and shorts.
- Care about speed, visual continuity, narration quality, and reuse of winning styles.
- Usually operate alone or with a very small team.

### 2. Agencies And Studio Teams

- Need collaboration, approval workflows, shared assets, and brand controls.
- Care about reuse across clients, export quality, and visibility into generation cost.
- Become the expansion audience after the creator workflow is stable.

## Product Promise

The platform should let a user go from brief to finished reel through a controlled pipeline:

1. Create a project from a topic, product, or campaign brief.
2. Generate multiple viral-style ideas and select one as the active concept.
3. Generate and edit a 60-120 second master script.
4. Split the script into 5-8 second scene segments.
5. Build a scene plan with reusable visual and voice presets plus start-frame and end-frame prompts per segment.
6. Generate scene frame pairs through a continuity chain where each scene can inherit the previous scene's approved end frame.
7. Generate video clips, narration, and supporting assets through async jobs.
8. Normalize source video audio, retime clips to narration where needed, and assemble a final export with subtitles, music, and narration.
9. Retry only the failing scenes or assets instead of restarting the entire render.

## What The Product Is Not

- It is not a raw prompt UI for one-off model calls.
- It is not a full video editing replacement in the first releases.
- It is not a local-only desktop app in the launch phase.
- It is not a promise of perfect cinematic continuity across all scenes.

## Product Principles

- Human approval before expensive generation steps.
- Async by default for all long-running work.
- Every output is versioned and retryable.
- One clear happy path for creators before broader studio capability.
- Commercial realism: heavy generation is usage-metered and observable.
- Continuity is a system concern, not something the user must solve manually scene by scene.

## Core Workflows

### Creator Workflow

- Create project
- Define brief
- Generate viral-style ideas
- Select one idea
- Generate or edit a master script
- Approve segmented scene plan with start/end prompts
- Review generated frame pairs
- Render reel
- Review assets and retry weak scenes
- Download final export

### Studio Workflow

- Create workspace and brand kit
- Share templates and approved visual presets
- Review work in progress
- Approve exports
- Track usage and cost by client or workspace

## Canonical Creator Pipeline

The canonical creator pipeline for the MVP is:

1. Generate a set of candidate ideas from the brief.
2. Select a single idea as the active concept.
3. Generate a 60-120 second script.
4. Segment the script into 5-8 second scenes.
5. Create start-frame and end-frame prompts for each scene.
6. Generate the first scene's start frame.
7. Generate the first scene's end frame using the start frame as reference.
8. Generate later scene frame pairs using the previous scene's approved end frame as a continuity anchor.
9. Generate a video clip for each scene from the scene text and frame pair.
10. Generate narration for each scene.
11. Strip or ignore provider-generated clip audio.
12. Retime the silent clip to the narration if needed.
13. Compose the full export with music, subtitles, and narration.

## System Components

- Web application for creators, editors, and admins
- API service for product workflows and domain operations
- Background orchestration layer for generation and assembly work
- Media generation adapters for text, image, video, and narration
- Asset storage and export library backed by MinIO-compatible object storage
- Billing, usage, and observability services
- Local or BYO execution agents in later phases

## Recommended Repository Structure

```text
reels-platform/
  apps/
    web/
    api/
    worker/
  packages/
    ui/
    config/
    schemas/
    sdk/
  infra/
    docker/
    compose/
    scripts/
  docs/
```

- `apps/web` should hold the React application.
- `apps/api` should hold the FastAPI application.
- `apps/worker` should hold Celery workers and FFmpeg-oriented job code.
- `packages/ui` should hold shared frontend components and design tokens if the repo grows beyond one app.
- `packages/schemas` should hold shared domain and contract definitions where cross-service reuse is valuable.
- `infra` should hold deployment, local dev orchestration, and operational scripts.
- `docs` should remain the source of truth for architecture and delivery planning.

## Success Metrics

- Time from brief to first export
- Percentage of renders completed without full restart
- Average number of scene retries per completed reel
- Credit cost per successful export
- Repeat usage of presets and templates
- Export completion rate per active creator

## Constraints And Assumptions

- Launch output is one primary format: 9:16 vertical reel.
- Launch target duration is 60-120 seconds with 5-8 second scene segments.
- The first usable release should prioritize continuity and control over maximum automation.
- The architecture must support hosted providers now and alternate providers later.
- Stored assets, prompts, and usage metadata are first-class product records, not disposable logs.
- A small engineering team should be able to implement the first releases without creating a distributed systems burden that is too heavy to operate.

## Release Strategy

- Phase 1 and Phase 2 establish the creator workflow and editable planning stages.
- Phase 3 is the first end-to-end render MVP.
- Phase 4 hardens reliability and introduces commercial controls.
- Phase 5 improves creator productivity and export quality.
- Phase 6 expands into collaboration and studio operations.
- Phase 7 adds local and bring-your-own-provider execution.
