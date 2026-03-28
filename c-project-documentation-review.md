# Project documentation review and update plan

**Scope:** Full review of `docs/` against the target creator pipeline (steps 0–10), stated technology choices, and operational needs.  
**Date:** 2026-03-28  
**Source of truth reviewed:** `docs/README.md`, `docs/01-project-overview.md`, `docs/02-roadmap-and-phase-index.md`, all `docs/architecture/*.md`, all phase folders under `docs/phases/`, and `docs/appendices/*`.

---

## Executive summary

The existing documentation is **strong on platform architecture**: job orchestration, consistency packs, keyframe review, provider abstraction, PostgreSQL + S3-compatible storage, FastAPI + Celery + Redis, React frontend, FFmpeg-based composition, moderation, auth, and phased delivery. It is **weaker on the exact generative workflow** you described—especially **paired start/end frame prompts**, **strict sequential image chaining across segments**, **muting model-generated video audio**, and **explicit time-stretch / tempo matching** of video to measured voiceover. **Vendor and runtime choices** (Azure OpenAI, Veo 3, MinIO, open-source models) are largely **unspecified** in the docs; integrations remain generic.

This report maps **gaps → recommended doc updates** (file-level) and adds **Python tooling suggestions** plus **optional services** aligned with your stack.

---

## 1. Alignment: your pipeline vs documented pipeline

| Your step | What docs already cover | Gap / mismatch |
| --- | --- | --- |
| **0. Generate viral ideas; select one** | Phase 1: idea generation from brief; `idea_sets` in data model | No “viral” positioning, hooks, or platform-specific formats; **select-one-from-list** UX and data transition (idea → active script seed) not spelled out end-to-end |
| **1. Script 1–2 min** | Script generation; versioning | **Duration target** in overview/roadmap emphasizes short reel (e.g. 30–60 s in consistency doc); **1–2 min** should be a first-class **export profile / brief constraint** or called out as product decision |
| **2. Split into 5–8 s sub-scripts** | Phase 2: “timing-safe” segments; glossary “Scene Segment” | Default language is **5–10 s** in composition doc; **5–8 s** should be documented as default segment policy or configurable range |
| **3. Per sub-script: start + end image prompts** | One **keyframe** per scene + scene visual prompts | Docs assume **single** approved keyframe → image-to-video. **No first-class “end frame” prompt**, end-state asset type, or provider contract for **first/last frame** video APIs |
| **4. Images: chain references (prev end → next start)** | Consistency pack, reference images, prompt construction | **Cross-scene chaining** (segment *n* end image as mandatory ref for segment *n+1*) is **not** specified; current model is pack + per-scene keyframe, not ordered **visual continuity chain** |
| **5. Video from sub-script + start/end pair** | Image-to-video preferred; text-to-video fallback | Adapter contract mentions optional reference image (singular). **Dual-reference (start/end)** and prompt-to-clip alignment per sub-script need architecture + integration docs |
| **6. Voiceover per sub-script** | Narration per scene; voice preset freeze | Aligned; ensure TTS step is ordered **after** final segment timing if step 8 adjusts duration |
| **7. Mute generated video audio** | Composition mixes **curated music + narration** | **Stripping or zeroing** audio tracks from **provider-returned clips** is **not documented**; risk of double audio if models return soundtrack |
| **8. Speed / stress video to voice length** | Freeze-frame pad if narration longer; trim if clip ≫ narration | **No dedicated time-stretch** (e.g. `setpts`, `atempo`) when clip length must match VO without black frames; “stress/fast” editorial intent not captured |
| **9–10. Assemble sequentially + render** | FFmpeg composition, concat, export | Largely aligned once per-scene A/V durations are defined |

---

## 2. Where documentation is comprehensive (keep as anchor)

These areas are already build-ready and should remain the backbone; updates should **extend** them rather than replace them.

| Area | Primary documents |
| --- | --- |
| Async jobs, retries, checkpoints, render job binding to approved versions | `architecture/05-job-orchestration-and-render-pipeline.md`, `architecture/04-data-model-and-storage.md` |
| Visual consistency philosophy, consistency pack, prompt assembly | `architecture/08-visual-consistency-and-asset-memory.md` |
| FFmpeg composition, ducking, loudness, narration sync, dependency gate | `architecture/14-composition-and-av-consistency.md`, `05-job-orchestration-and-render-pipeline.md` |
| Provider adapters, routing, failure taxonomy | `architecture/06-provider-abstraction-and-integration-architecture.md` |
| Phase sequencing (plan before expensive render) | `02-roadmap-and-phase-index.md`, phase overviews |
| API shape at high level | `appendices/01-api-surface-and-endpoint-catalog.md` |
| Security, deployment units, signed URLs | `architecture/07-deployment-observability-and-security.md` |

---

## 3. Where documentation is not comprehensive (gaps)

### 3.1 Product and workflow specificity

- **“Viral” idea generation:** No templates for hooks, trends, or pattern-of-the-day; no metrics for “idea quality” or A/B of titles.
- **Explicit pipeline parity:** The numbered steps you listed are not mirrored as a single **canonical user journey** diagram in any one doc (overview fragments vs your checklist).
- **Idea → single selected concept:** Selection state, locking, and regeneration rules for unselected ideas are not detailed.

### 3.2 Scene and asset model

- **Two prompts / two stills per segment:** Schema for `scene_segments` (or equivalent) does not describe **start_frame_prompt**, **end_frame_prompt**, **start_image_asset_id**, **end_image_asset_id** (or variant types).
- **Chained generation graph:** No document defines **generation order** and **hard dependency**: image for scene *i* depends on **end image** of scene *i−1* (and how scene 1 seeds from consistency pack only).

### 3.3 Video generation contract

- **Veo 3 (or any first/last frame API):** No mention of frame-pair inputs, duration limits, or audio-in-clip behavior.
- **Open-source video models:** No guidance on self-hosting, GPU workers, licensing, or adapter equivalence matrix entries.

### 3.4 Audio and post-sync

- **Strip video audio:** Missing render step or composition pre-step: **demux / `-an` intermediate** or `anullsrc` replacement before final mix.
- **Time remapping:** Missing specification for matching clip duration to **measured TTS duration** using **speed change** vs only pad/trim (current docs emphasize pad/trim).

### 3.5 Technology stack naming

- **MinIO:** Docs refer to **S3-compatible** storage only; **MinIO** as dev/staging default is not named in architecture or deployment.
- **Azure OpenAI:** Not listed as a concrete text/image/TTS integration; only generic “hosted providers.”
- **PostgreSQL:** Implied; entity list is clear—minor naming consistency (you wrote “PostgreesSql”).
- **Docker:** Present for local Compose; could explicitly list **services** (api, worker, postgres, redis, minio, beat).

### 3.6 “Nano banana”

- Not referenced anywhere in the repo docs. **Action:** Clarify product name or model (e.g. typo, internal codename, or a specific image API). Until then, add a **decision-log stub** or glossary note once defined.

---

## 4. Update plan by document (actionable)

### 4.1 `docs/01-project-overview.md`

- Add a subsection **Canonical reel pipeline (v1)** mirroring your steps 0–10 in product language (not only internal job names).
- Resolve **target length**: state whether MVP is **~60 s max**, **1–2 min**, or **configurable per project**; align success metrics and phase scope.
- Under workflows, add **Select idea → lock concept** before script generation.

### 4.2 `docs/02-roadmap-and-phase-index.md`

- In Phase 2 / Phase 3 table rows, add one line each on **segment duration policy** (5–8 s vs 5–10 s) and **paired keyframes** if adopted for MVP or Phase 3.x.

### 4.3 `docs/architecture/05-job-orchestration-and-render-pipeline.md`

- Extend pipeline stages to include optional (or required) substeps:
  - **End-frame image generation** (or paired generation) per scene.
  - **Sequential image dependency** between scenes (enqueue order or explicit step DAG).
  - **Video audio strip** after video generation (or as first composition input filter).
  - **Duration alignment** substep: measure narration duration → **retime** video (FFmpeg `setpts` / `atempo` chain) within tolerance, then existing pad/trim rules.
- Update render step types in prose (and later in data model appendix) so workers are not ambiguous.

### 4.4 `docs/architecture/08-visual-consistency-and-asset-memory.md`

- Document **when** to use consistency pack-only vs **previous-scene end frame** as additional reference (your chain).
- Add **asset memory** entries for **end keyframe** and **inter-scene reference edge** (which asset ID propagates forward).
- Clarify interaction with keyframe review: approve **start only**, **end only**, or **both** before video.

### 4.5 `docs/architecture/14-composition-and-av-consistency.md`

- Add **Input video audio policy**: default **discard** provider audio track; final mix uses **narration + music** only unless a feature flag enables model audio.
- Expand **duration sync** to three strategies in order: (1) **retime** clip to narration within min/max speed bounds; (2) freeze-frame pad if narration longer after max stretch; (3) trim if still excessive—align with orchestration doc.
- Note **Python implementation** still builds **FFmpeg filter graphs** (see section 6).

### 4.6 `docs/architecture/06-provider-abstraction-and-integration-architecture.md`

- Extend modality table: **Image generation** with **reference_image_ids[]** (ordered: primary ref + optional style refs).
- **Video generation**: inputs **start_frame**, optional **end_frame**, **script text**, **duration**; output **has_audio_stream** boolean for downstream strip step.
- Add **equivalence matrix** row: providers that support **end frame** vs **single keyframe only**.

### 4.7 `docs/architecture/04-data-model-and-storage.md`

- Extend `asset_type` or use variants: e.g. `image_keyframe_start`, `image_keyframe_end` (or metadata on `image` rows: `keyframe_role`).
- Optional: `scene_segment` fields for **chained_from_asset_id**.
- Storage layout: under `assets/images/`, convention for **start** vs **end** per `scene_segment_id`.

### 4.8 `docs/phases/phase-2-content-planning/*`

- **Overview / implementation-plan:** Segmenter targets **5–8 s** (or configurable); store **start/end visual prompt** fields in scene plan UI and API.
- **Integrations:** If segmentation uses an LLM, name **Azure OpenAI** as example primary with abstention for actual vendor lock-in wording.

### 4.9 `docs/phases/phase-3-render-mvp/*`

- **Overview / architecture / integrations:**  
  - Pair **image gen** (start + end, chained).  
  - **Video gen** (Veo 3–style API **and** OSS path as secondary).  
  - **Post-video:** mute track; **sync** step before composition.  
- **Exit criteria:** E2E reel matches **VO duration per segment** within defined tolerance.

### 4.10 `docs/architecture/07-deployment-observability-and-security.md`

- Optional **compose profile** listing: Postgres, Redis, MinIO, API, workers, frontend dev proxy.
- If OSS video runs on GPU: **separate worker pool** / autoscaling note (queue depth already documented—tie to GPU worker type).

### 4.11 `docs/README.md`

- Add “**Target stack (reference)**” bullet list: React, FastAPI, PostgreSQL, MinIO, Docker, Azure OpenAI, Veo 3, OSS fallbacks—marked as **configurable via adapters**.

### 4.12 `docs/appendices/01-api-surface-and-endpoint-catalog.md`

- Endpoints for **paired prompts** on scene patch payload; optional **regenerate end frame only**.
- Webhook or SSE events if **chained** step fails mid-chain (partial job recovery).

### 4.13 `docs/appendices/02-domain-glossary.md`

- Terms: **Start keyframe**, **End keyframe**, **Inter-scene reference chain**, **Video audio strip**, **Clip retime**.

### 4.14 `docs/appendices/04-decision-log.md`

- Record decisions: default segment length; paired frames vs single keyframe; mute policy; primary vendors (Azure OpenAI, Veo 3, MinIO); definition of “nano banana” when confirmed.

### 4.15 `docs/appendices/03-risk-register.md`

- New risks: **APIs without end-frame support** (fallback strategy); **chained jobs** amplify failure rate; **double audio** if strip step skipped; **time-stretch** artifacts on short clips.

---

## 5. Python: video editing and rendering suggestions

The docs already standardize on **FFmpeg** for composition. For **Python**, prefer **thin orchestration + FFmpeg** over heavy NLE-style tools for server-side batch work.

| Library / tool | Role |
| --- | --- |
| **ffmpeg-python** or **PyAV** | Build filter graphs, strip audio (`-map 0:v`), concat, `setpts`, `atempo`, `loudnorm`, burn-in subs—matches `14-composition-and-av-consistency.md`. |
| **MoviePy** | Faster prototyping and some high-level cuts; still FFmpeg under the hood; watch long-run stability in workers vs raw FFmpeg. |
| **pydub** | Simple WAV/MP3 edits; less ideal for video; optional for quick narration trims. |
| **ffprobe** (subprocess) | Already implied by “asset stream probe”—keep for validation. |

**Rendering:** treat **libx264** (or **libsvtav1** if you need efficiency) + **AAC** as the default export path; **faststart** for progressive download—already reflected in composition doc examples.

---

## 6. Additional services to consider

| Service | Why |
| --- | --- |
| **Reverse proxy + TLS** (e.g. Traefik, Caddy, nginx) | Termination in front of API and MinIO in Compose/production-shaped dev |
| **Managed Postgres + Redis** | Already assumed for prod; local uses containers |
| **CDN** | React static assets and signed export delivery offload (optional behind same object store) |
| **Secret manager** | Docs already specify cloud KMS; map **Azure Key Vault** explicitly if Azure-first |
| **GPU nodes or serverless GPU** | Only if **open-source video** or heavy image batching is on critical path |
| **Email / transactional notifications** | Password reset, render complete—referenced in architecture phases |
| **Error tracking** (e.g. Sentry-class) | Operational—not always in docs; worth one line in observability |
| **Idempotency / dedup store** | Optional Redis keys for provider webhook idempotency if vendors send async callbacks |

---

## 7. Recommended sequencing for doc work

1. **Decision log + overview** — Lock duration targets, paired frames, mute policy, and vendor names.  
2. **Data model + orchestration** — So engineering has one schema and step DAG story.  
3. **Visual consistency + composition** — Chain rules and FFmpeg behavior.  
4. **Provider abstraction + Phase 3 integrations** — Concrete adapter fields (Azure OpenAI, Veo 3, MinIO, OSS).  
5. **Appendices** — Glossary, API payloads, risk register.

---

## 8. Summary table: completeness scorecard

| Topic | Comprehensiveness |
| --- | --- |
| Auth, workspaces, rate limits, moderation | **High** |
| Job orchestration, retries, checkpoints | **High** |
| Single keyframe + image-to-video | **Medium–high** |
| Paired start/end frames + cross-scene chaining | **Low (missing)** |
| Mute model audio on clips | **Low (missing)** |
| Time-stretch / “stress” to VO | **Low (partial—pad/trim only)** |
| Named stack (MinIO, Azure OpenAI, Veo 3, OSS) | **Low (generic)** |
| “Viral” idea product framing | **Low** |
| Python media stack specifics | **Low (FFmpeg implied, libraries not listed)** |

---

*End of report.*
