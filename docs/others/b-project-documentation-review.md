# Project Documentation Review And Update Plan

Date: 2026-03-28

Scope reviewed:
- Entire `docs/` tree
- New review comments describing the desired 0-10 production workflow
- Current provider/tool availability checked against official docs for Azure OpenAI, Google Vertex AI, MoviePy, PyAV, ffmpeg-python, and selected open models

## Executive Summary

The current docs are strong at the platform-architecture level. They already cover:
- React + FastAPI + PostgreSQL + async workers
- provider abstraction
- asset storage
- render orchestration
- keyframe review
- FFmpeg-based composition
- moderation, billing, auth, and future BYO/local execution

However, the docs are **not yet comprehensive for the workflow you now want**.

The biggest gap is that the documentation still describes a **single-keyframe-per-scene pipeline**, while your new workflow requires a **paired-frame, chained-reference pipeline**:
- start image + end image per sub-script
- each next scene anchored to the previous scene's end image
- video generation from both start and end visual references
- explicit muting/removal of provider-generated clip audio
- explicit speed/stretch rules to match narration length

There is also a major requirements mismatch on duration:
- current docs assume roughly **30-60 seconds total** and **5-10 second scenes**
- your new comments require **1-2 minute videos** and **5-8 second segments**

That single change affects the product overview, scene planning heuristics, render job cost model, quotas, scene count assumptions, UI scale, and provider compatibility.

## Overall Assessment

### What is already aligned

- React frontend, FastAPI backend, PostgreSQL, Docker, and object storage all fit the product shape.
- S3-compatible storage already maps well to MinIO.
- FFmpeg-based composition remains the right foundation.
- Celery + Redis is already a reasonable MVP orchestration choice.
- The provider adapter approach is exactly the right abstraction for mixing Azure-hosted, Google-hosted, and open/local models later.

### Where the docs are currently not comprehensive

- No first-class "viral idea selection" stage after idea generation.
- No canonical model for **start prompt + end prompt** per segment.
- No data model for **paired scene images** or **reference chaining** across scenes.
- No provider contract for **first-frame + last-frame video generation**.
- No explicit rule for **silent video generation** or **source audio stripping**.
- No precise strategy for **voice-length matching** beyond freeze-frame pad / trim.
- No vendor shortlist or capability matrix, even though your comments now name likely provider families.
- No licensing/commercial-readiness guidance for open-source image/video/audio models.
- No Python library selection guidance for composition, media probing, and timing alignment.

## Canonical Workflow The Docs Should Now Describe

1. Generate multiple viral-style ideas.
2. Select one idea as the active concept.
3. Generate a 60-120 second master script.
4. Split the script into 5-8 second scene/sub-script segments.
5. Generate a start prompt and end prompt for each segment.
6. Generate the first segment's start image.
7. Generate the first segment's end image using the first start image as reference.
8. Generate the next segment's start/end images using the previous segment's end image as the continuity anchor.
9. Generate a video clip from each segment using the segment text plus the paired visual references.
10. Generate voiceover per segment.
11. Remove or ignore provider-generated clip background audio.
12. Align each clip duration to narration length using bounded speed-change/pad/trim rules.
13. Assemble all segment clips and narration sequentially.
14. Render the final export.

## Workflow Coverage Review

| Step | Current coverage | Gap | Priority | Docs to update |
| --- | --- | --- | --- | --- |
| 0. Generate viral ideas | Partial | Idea generation exists, but "viral" framing, scoring, ranking, and idea selection are missing | High | `docs/01-project-overview.md`, `docs/phases/phase-1-foundation/*`, `docs/appendices/01-api-surface-and-endpoint-catalog.md`, `docs/appendices/02-domain-glossary.md` |
| Select one idea | Missing | No explicit selected-idea state or endpoint | High | same as above |
| 1. Generate 1-2 min script | Partial | Script generation exists, but docs still assume shorter output windows | High | `docs/01-project-overview.md`, `docs/phases/phase-2-content-planning/02-architecture.md`, `docs/architecture/14-composition-and-av-consistency.md`, `docs/appendices/04-decision-log.md` |
| 2. Divide into 5-8 sec segments | Partial | Segmentation exists, but current docs say 5-10 sec and 25-65 sec total | High | `docs/phases/phase-2-content-planning/*`, `docs/architecture/08-visual-consistency-and-asset-memory.md`, `docs/architecture/14-composition-and-av-consistency.md` |
| 3. Generate start and end image prompts | Missing | Scene planning mentions "visual prompt hints" only; prompt pairs do not exist | High | `docs/architecture/04-data-model-and-storage.md`, `docs/phases/phase-2-content-planning/*`, API appendix, glossary |
| 4. Generate start/end images with chained references | Partial | Docs only model one keyframe per scene; no pair model or previous-scene chaining | Critical | `docs/architecture/05-job-orchestration-and-render-pipeline.md`, `docs/architecture/08-visual-consistency-and-asset-memory.md`, `docs/phases/phase-3-render-mvp/*`, glossary, decision log |
| 5. Generate video clip from sub-script + paired images | Partial | Docs prefer image-to-video from one approved keyframe; no first+last frame contract | Critical | `docs/architecture/06-provider-abstraction-and-integration-architecture.md`, `docs/phases/phase-3-render-mvp/04-integrations.md`, API appendix |
| 6. Generate voiceover for all sub-scripts | Good | Covered, but needs duration snapshot fields and pacing rules | Medium | `docs/architecture/04-data-model-and-storage.md`, `docs/architecture/14-composition-and-av-consistency.md` |
| 7. Mute generated video background sound | Missing | No provider-level silent video rule and no mandatory source-audio stripping step | Critical | `docs/architecture/05-job-orchestration-and-render-pipeline.md`, `docs/architecture/14-composition-and-av-consistency.md`, `docs/phases/phase-3-render-mvp/02-architecture.md` |
| 8. Stretch/speed to match voice length | Partial | Docs mention freeze-frame pad or trim, but not bounded speed-up/slow-down policy | High | `docs/architecture/14-composition-and-av-consistency.md`, `docs/architecture/05-job-orchestration-and-render-pipeline.md`, risk register |
| 9. Sequential assembly and merge | Good | Covered, but needs the new pre-composition audio and timing rules | Medium | `docs/architecture/14-composition-and-av-consistency.md` |
| 10. Render final video | Good | Already covered | Low | minor cleanup only |

## Highest-Impact Corrections

### 1. Duration assumptions are now wrong across the docs

Current documented assumptions:
- 30-60 second reel
- 25-65 second warnings
- 5-10 second scene guidance

New requirement:
- 60-120 second video
- 5-8 second target segments

Impact:
- more scenes per job
- more image generations
- more narration jobs
- more provider cost
- more queue pressure
- more SSE events
- more asset storage
- more complex UI timelines

Required action:
- update all duration guidance to a single canonical rule
- explicitly state expected scene count range for 60-120 seconds
- revise Phase 4 cost/quota assumptions accordingly

### 2. The docs must move from "single keyframe" to "frame pair + continuity chain"

Current model:
- one approved keyframe per scene
- keyframe review
- image-to-video from that single image

Needed model:
- `start_frame_image`
- `end_frame_image`
- `reference_chain_parent_asset_id`
- prompt pair per segment
- review/approval of the frame pair, not just one image

This is the biggest architectural mismatch in the current docs.

### 3. Background audio handling is underspecified

Your desired workflow explicitly says:
- generate video clip
- mute all generated background sound

The current docs only talk about music underlay and narration mix. They do **not** define what happens if the video provider returns audio.

The docs need a hard rule:
- if the provider supports silent output, request silent output
- otherwise strip clip audio immediately after generation
- composition always uses narration + approved music bed, not source clip audio

### 4. Provider decisions can no longer stay fully deferred

The docs currently keep provider vendors as a deferred decision. That made sense earlier, but your new comments now name likely provider families and impose workflow-specific capabilities:
- image editing/reference consistency
- first/last-frame video generation
- optional silent video generation
- TTS per segment
- open/local fallback

The docs now need at least:
- a provider shortlist
- a capability matrix
- a licensing/commercial-readiness matrix

## File-By-File Update Plan

### Top-level docs

| File | Required update |
| --- | --- |
| `docs/README.md` | Add one paragraph stating that the media pipeline now supports scene prompt pairs, chained reference images, and silent video normalization before composition. Add a pointer to a new provider capability matrix appendix. |
| `docs/01-project-overview.md` | Rewrite the product promise and creator workflow to include idea selection, 60-120 second scripts, 5-8 second segments, paired prompts, paired images, chained reference continuity, and muted source video audio. |
| `docs/02-roadmap-and-phase-index.md` | Update phase summaries so Phase 2 explicitly includes prompt-pair planning and Phase 3 includes paired-frame generation, source-audio removal, and clip-to-voice alignment. |

### Architecture docs

| File | Required update |
| --- | --- |
| `docs/architecture/01-system-context.md` | Expand the core data/control flow to mention start/end image generation, chained references, narration timing capture, and silent clip normalization. |
| `docs/architecture/04-data-model-and-storage.md` | Add fields/entities for selected idea, scene prompt pair, start frame, end frame, continuity parent asset, narration duration metrics, clip timing-alignment strategy, and source-audio policy. |
| `docs/architecture/05-job-orchestration-and-render-pipeline.md` | Replace the single-keyframe-centric render stage list with prompt-pair generation, paired image generation, frame-pair review, chained continuity, source-audio removal, and explicit duration-alignment rules. |
| `docs/architecture/06-provider-abstraction-and-integration-architecture.md` | Add provider capabilities for image editing, multi-image/reference input, first+last frame video generation, silent output, 9:16 support, and open-model license checks. |
| `docs/architecture/07-deployment-observability-and-security.md` | Name MinIO as the selected S3-compatible storage implementation for local/dev or self-hosted deployments. Add GPU worker pools for local/open-source paths and add license/compliance alerting for open models. |
| `docs/architecture/08-visual-consistency-and-asset-memory.md` | Rework consistency flow around frame pairs and previous-scene end-frame chaining. Define whether the next scene is anchored to prior end frame only, or also to scene/global consistency pack references. |
| `docs/architecture/14-composition-and-av-consistency.md` | Add mandatory clip-audio stripping, bounded speed-up/slow-down policy, per-scene timing reconciliation order, and rules for composing 60-120 second exports made of 5-8 second units. |

### Phase docs

| File set | Required update |
| --- | --- |
| `docs/phases/phase-1-foundation/*` | Add idea scoring/selection and define whether "viral" is heuristic-only or trend-grounded. Add selected-idea state as the handoff into script generation. |
| `docs/phases/phase-2-content-planning/*` | Change segmentation guidance to 5-8 seconds. Add start/end prompt generation, editing, preview, and approval. Add voice-duration estimation fields per segment. |
| `docs/phases/phase-3-render-mvp/*` | Replace single-keyframe review with frame-pair generation/review where needed, add chained reference logic, add first/last-frame video contract, add silent-video handling, and add timing-alignment implementation details. |
| `docs/phases/phase-4-reliability-and-billing/*` | Recalculate credit assumptions for 60-120 second jobs with doubled image assets per scene. Add failure/retry rules for prompt-pair generation and paired-image regeneration. |
| `docs/phases/phase-5-polish-and-creator-productivity/*` | Add reusability rules for prompt pairs and continuity chains, not just single keyframes. |
| `docs/phases/phase-7-local-and-byo-expansion/*` | Add capability flags for open-source image editing, I2V, FLF2V, and local TTS. Add licensing governance for open-source models. |

### Appendix docs

| File | Required update |
| --- | --- |
| `docs/appendices/01-api-surface-and-endpoint-catalog.md` | Add endpoints for selecting an idea, generating/editing scene prompt pairs, reviewing frame pairs, and exposing timing-alignment details in render status. |
| `docs/appendices/02-domain-glossary.md` | Add `Selected Idea`, `Scene Prompt Pair`, `Start Frame`, `End Frame`, `Reference Chain`, `Source Audio Policy`, `Timing Alignment Strategy`, and `Continuity Anchor`. |
| `docs/appendices/03-risk-register.md` | Add risks for duration expansion, audio bleed from provider clips, continuity drift accumulation across chained references, preview-provider constraints, and open-model license restrictions. |
| `docs/appendices/04-decision-log.md` | Record decisions on 60-120 second outputs, 5-8 second targets, frame-pair workflow, silent clip policy, provider shortlist, and Python media-tooling choices. |

## New Docs I Recommend Adding

### 1. `docs/architecture/15-scene-frame-pair-and-reference-chain.md`

Purpose:
- make the new start-frame/end-frame workflow explicit
- define how chaining works scene to scene
- define fallback behavior when one frame fails
- define how approval works for frame pairs

This should be a dedicated architecture doc, not buried inside the existing keyframe doc.

### 2. `docs/appendices/05-provider-capability-matrix.md`

Purpose:
- compare image/video/audio providers against the actual workflow needs
- capture 9:16 support
- capture first-frame/last-frame support
- capture silent-video support
- capture editing/reference-image support
- capture licensing/commercial restrictions

### 3. `docs/appendices/06-python-media-tooling-and-service-selection.md`

Purpose:
- document the Python composition stack
- document FFmpeg vs PyAV vs MoviePy roles
- document timing-alignment tools and when to use them
- document MinIO, Redis, observability, and secret-management choices

## API And Data Model Additions To Plan For

### Suggested API additions

- `POST /api/v1/projects/{project_id}/ideas/{idea_id}:select`
- `POST /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}:generate-prompt-pairs`
- `PATCH /api/v1/projects/{project_id}/scene-plans/{scene_plan_id}/segments/{segment_id}`
  - should include `start_image_prompt` and `end_image_prompt`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:approve-frame-pair`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:regenerate-start-frame`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:regenerate-end-frame`
- `POST /api/v1/renders/{render_job_id}/steps/{step_id}:regenerate-frame-pair`

### Suggested data additions

- `projects.selected_idea_id` or an equivalent selected-idea relation
- `scene_segments.start_image_prompt`
- `scene_segments.end_image_prompt`
- `scene_segments.target_duration_seconds`
- `scene_segments.estimated_voice_duration_seconds`
- `scene_segments.actual_voice_duration_seconds`
- `assets.asset_role`
  - `scene_start_frame`
  - `scene_end_frame`
  - `continuity_anchor`
- `assets.parent_asset_id` for chain lineage
- `render_steps.source_audio_policy`
  - `request_silent`
  - `strip_after_generation`
  - `preserve`
- `render_steps.timing_alignment_strategy`
  - `none`
  - `speed_adjust`
  - `freeze_pad`
  - `trim`

## Recommended Technical Decisions

These are the recommendations I would now document explicitly.

### Image generation

| Option | Recommendation | Why it fits the new workflow |
| --- | --- | --- |
| Azure OpenAI | Use `gpt-image-1.5` or `gpt-image-1` as the Azure-first hosted image path | Azure's current image docs describe text + image input, editing/variations, and face-preservation style capabilities, which fit your start/end image editing flow better than plain text-to-image only |
| Gemini 2.5 Flash Image | Treat `Gemini 2.5 Flash Image` as the official name, with "nano banana" only as an alias in notes | Google's current materials emphasize multi-image fusion and character/style consistency, which directly matches your chained reference workflow |
| Open-source image path | Only enable reference-aware open models after license review; do not assume generic open image models are commercially safe | Current open-image options are uneven on editing/reference control and some popular choices are non-commercial by default |

### Video generation

| Option | Recommendation | Why it fits the new workflow |
| --- | --- | --- |
| Hosted primary | Use Veo 3.1 as the primary hosted video path if you want first+last frame generation | Current Vertex AI docs explicitly support 9:16, 4/6/8 second clips, and first/last frame inputs |
| Silent-video policy | For Veo 3 models, set `generateAudio=false` when the workflow wants narration-only composition | This matches your step to mute background sound and avoids unwanted provider-generated audio entering the timeline |
| Open/local path | Use Wan2.1 I2V and Wan2.1 FLF2V as the local/BYO video candidates | Wan2.1 currently exposes both image-to-video and first-last-frame-to-video variants, which maps well to your paired-image workflow |

Important note:
- Veo 3 durations are currently constrained to **4, 6, or 8 seconds**
- your docs currently want **5-8 second** segments

That means the docs should define one of these policies:
- target **6-8 second** scenes for the Veo path
- or allow **5-8 second** authored scenes but normalize generated clips to that range after generation

### Audio generation

| Option | Recommendation | Why it fits the new workflow |
| --- | --- | --- |
| Azure-hosted primary | Use `gpt-4o-mini-tts` as the primary Azure OpenAI TTS path | It is the cleanest current Azure-hosted TTS choice for per-scene voiceover generation |
| Open-source fallback | Use XTTS-v2 for multilingual voice cloning if local/BYO voice cloning matters | XTTS-v2 is still a strong local cloning option for scene-by-scene narration consistency |
| Lightweight English fallback | Consider Kokoro if you need a cheap, light open-weight English TTS path | It is much lighter than XTTS and easier to run locally, but is narrower in scope |

### Python video editing and rendering

My recommendation is:
- use **FFmpeg as the rendering engine**
- use **ffmpeg-python** or a typed FFmpeg wrapper to build filter graphs in Python
- use **ffprobe** for validation
- use **PyAV only where exact packet/frame access is actually needed**
- keep **MoviePy** as a prototype/helper tool only, not the core production compositor

Reasoning:
- the current docs already center FFmpeg, which is correct
- `ffmpeg-python` is a good fit for programmatic filter graph construction
- PyAV itself says it is best used when the plain `ffmpeg` command is not enough
- MoviePy is still good for quick experiments, but your production workflow is already complex enough that FFmpeg should remain the source of truth

### Timing-alignment policy to document

The current docs need a stricter rule set. I recommend documenting:

1. Prefer generating scene clips near the target narration duration.
2. If clip and narration differ slightly, allow bounded speed adjustment first.
3. If narration is longer after bounded adjustment, freeze-pad the clip.
4. If clip is much longer, trim or modestly speed-match it.
5. Never keep provider-generated source audio in the final mix.

Suggested default bounds:
- clip speed adjustment: `0.92x` to `1.08x`
- narration speed change: avoid by default unless explicitly enabled by preset
- beyond bounds: use freeze-pad or trim, not extreme speed warping

## Additional Services To Explicitly Add

Your new "Tech use" list is close, but a few services are still missing and should be documented explicitly.

### Required

- `Redis`
  - already assumed throughout the docs for Celery, SSE buffering, rate limiting, and quotas
- `Secret manager`
  - Azure Key Vault if you stay Azure-first
- `Observability stack`
  - metrics, traces, structured logs, and error tracking
- `Email/notification provider`
  - for invites, failures, and keyframe/frame-pair review reminders

### Recommended

- `CDN or edge delivery layer`
  - for export downloads and preview assets
- `Billing provider`
  - only when you reach Phase 4 commercial controls

### Optional, not required yet

- trend-ingestion service for real-time "viral idea" grounding
  - only add this if "viral" must mean grounded in live signals rather than LLM heuristics
- workflow engine replacement for Celery
  - not needed yet; current docs are still coherent with Celery + Redis

### Services I would not add yet

- vector database
- generic agent framework
- full non-linear editor service

None of those are required to implement the workflow you described.

## Priority Order For Documentation Updates

### P0: Must change first

- duration assumptions
- idea selection stage
- prompt-pair model
- frame-pair + continuity-chain architecture
- first/last-frame video contract
- silent clip audio policy

### P1: Must change before implementation starts

- API appendix
- data model appendix and glossary
- phase 2 planning docs
- phase 3 render docs
- provider capability matrix
- open-model licensing guidance

### P2: Should follow immediately after

- Phase 4 cost/quota recalibration
- Phase 5 reuse/template updates for prompt pairs and continuity chains
- Phase 7 local/BYO capability updates
- README and roadmap cleanup

## Recommended Documentation Sequence

1. Update `01-project-overview.md` and `02-roadmap-and-phase-index.md`.
2. Update `04-data-model-and-storage.md`, `05-job-orchestration-and-render-pipeline.md`, `08-visual-consistency-and-asset-memory.md`, and `14-composition-and-av-consistency.md`.
3. Add the new frame-pair/reference-chain architecture doc.
4. Update Phase 2 and Phase 3 docs.
5. Update API catalog, glossary, risk register, and decision log.
6. Add provider capability matrix and Python tooling appendix.
7. Revisit Phase 4 and Phase 7 for cost, licensing, and local execution implications.

## Final Recommendation

The docs are a good foundation, but they currently document the wrong render primitive for your new workflow.

Right now the system is documented as:
- approved script
- segmented scenes
- one keyframe per scene
- image-to-video
- narration
- composition

Your new workflow requires the docs to instead standardize on:
- selected viral idea
- 60-120 second master script
- 5-8 second segments
- start/end prompt pair per segment
- paired image generation with previous-scene continuity chaining
- first/last-frame video generation
- per-scene narration
- silent clip normalization
- bounded timing alignment
- sequential composition and final render

That should become the new canonical spec before implementation work continues.

## Source Notes For Current Tooling Recommendations

Official/current references checked during this review:

- Azure OpenAI image generation docs:
  - https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/dall-e
- Azure OpenAI audio generation quickstart:
  - https://learn.microsoft.com/en-us/azure/foundry/openai/audio-completions-quickstart
- Veo API reference:
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation
- Veo first/last frame guide:
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames
- Gemini 2.5 Flash Image / "nano banana" overview:
  - https://cloud.google.com/blog/products/ai-machine-learning/gemini-2-5-flash-image-on-vertex-ai
- MoviePy user guide:
  - https://zulko.github.io/moviepy/user_guide/index.html
- PyAV documentation:
  - https://pyav.org/docs/develop/index.html
- ffmpeg-python:
  - https://github.com/kkroening/ffmpeg-python
- Wan2.1 FLF2V and I2V model cards:
  - https://huggingface.co/Wan-AI/Wan2.1-FLF2V-14B-720P
  - https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-480P
- XTTS-v2 model card:
  - https://huggingface.co/coqui/XTTS-v2
- Kokoro model card:
  - https://huggingface.co/hexgrad/Kokoro-82M
- FLUX Kontext license/model page:
  - https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev
  - https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/blob/main/LICENSE.md

Notes:
- I am inferring the final architecture recommendations from those sources plus the current local docs.
- The main actionable conclusion is not "pick every named provider now," but "document a capability and licensing matrix now, because your workflow depends on those capabilities."
