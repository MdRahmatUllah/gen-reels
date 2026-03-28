# Reels Generation Platform — Documentation Review & Update Plan

> **Review Date:** 2026-03-28  
> **Scope:** Full `docs/` directory vs. the revised 10-step workflow and updated tech stack requirements

---

## Executive Summary

The current documentation is **architecturally mature** — 14 architecture docs, 7 phase folders, and 4 appendices cover system context, frontend/backend architecture, data models, job orchestration, provider abstraction, deployment, and more. However, when compared against the **revised workflow** and **updated tech stack**, there are **significant gaps** in concrete provider mapping, several missing pipeline steps, an outdated storage assumption, and no containerization strategy. This report identifies every gap, rates its severity, and proposes where and how to update.

---

## 1. Workflow Gap Analysis

The table below maps each step in the revised workflow to its coverage in the current docs.

| # | Revised Workflow Step | Current Doc Coverage | Gap Severity |
|---|---|---|---|
| 0 | **Generate viral ideas** → select one | ✅ Covered in pipeline stages 1–2, Phase 1 | 🟡 Partial — "viral" angle not addressed |
| 1 | **Generate script** (1–2 min video) | ✅ Covered in pipeline stage 3, Phase 1 | 🟡 Partial — duration is "30–60s" not "1–2 min" |
| 2 | **Divide script** into 5–8 second sub-scripts | ✅ Covered in pipeline stage 4 (scene segmentation) | ✅ Good |
| 3 | **Generate start & end image prompts** per sub-script | 🔴 **Not covered** — docs mention one keyframe per scene, not start+end pairs | 🔴 Critical |
| 4 | **Generate images** with chained reference continuity | 🟡 Partially covered by consistency pack, but no **sequential reference chaining** (image N references image N-1's end frame) | 🔴 Critical |
| 5 | **Generate video clips** from start+end image pairs | 🟡 Docs cover image-to-video with single keyframe. **No start-to-end image interpolation model** is documented | 🔴 Critical |
| 6 | **Generate voiceover** for all sub-scripts | ✅ Covered in pipeline stage 13, Phase 3 | ✅ Good |
| 7 | **Mute background sound** from generated videos | 🔴 **Not covered** — no audio stripping step exists in the pipeline | 🟠 High |
| 8 | **Stretch/speed-match** each clip to voice duration | 🟡 Partially covered — docs mention freeze-frame pad and trim, but **not time-stretching (speed-up/slow-down)** | 🟠 High |
| 9 | **Assemble & merge** all video+voice sequentially | ✅ Covered in composition doc (14) | ✅ Good |
| 10 | **Render final video** | ✅ Covered in composition and export | ✅ Good |

### Critical Gaps Summary

1. **Start + End Image Pair Model** (Steps 3–5): The entire image generation model assumes one keyframe per scene. The revised workflow requires **two images per sub-script** (start frame and end frame) with the end frame used as the reference for the next sub-script's start. This fundamentally changes the generation pipeline, data model, and consistency pack logic.

2. **Sequential Reference Chaining** (Step 4): The docs enforce consistency via a static consistency pack. The revised workflow requires **dynamic chaining** — each sub-script's images reference the previous sub-script's outputs, creating a **linear dependency chain** rather than a parallel-per-scene approach.

3. **Audio Stripping from Generated Video** (Step 7): No pipeline stage addresses muting or extracting the audio track from AI-generated videos. Generated video clips from models like Veo3 may include ambient/default audio that must be removed before voiceover overlay.

4. **Time-Stretching / Speed Matching** (Step 8): The docs mention freeze-frame padding (extend) and trimming (shorten), but not **playback speed adjustment** (e.g., 1.2× or 0.8× to match voiceover duration). This is a fundamentally different technique.

---

## 2. Tech Stack Gap Analysis

| Component | Current Docs Say | Revised Requirement | Gap |
|---|---|---|---|
| **Image Generation** | Generic "provider adapters" | Azure OpenAI, Banana (nano banana), open-source models | 🔴 No concrete provider adapters specified |
| **Video Generation** | Generic "provider adapters" | Veo3 API, open-source video gen models | 🔴 No Veo3 adapter or open-source video model adapter documented |
| **Audio Generation** | Generic "SpeechProvider" | Azure OpenAI TTS, open-source TTS models | 🟡 Interface exists but no concrete adapters |
| **Object Storage** | S3-compatible (generic) | **MinIO** (self-hosted) | 🟠 MinIO not mentioned; deployment and config need updates |
| **Containerization** | Docker Compose for local dev only | **Docker** as primary container strategy | 🟠 No Dockerfile specs, no production container strategy doc |
| **Video Editing Library** | FFmpeg only | Python library suggestion needed (MoviePy, etc.) | 🟡 FFmpeg is covered; Python wrapper not discussed |
| **Video Rendering** | FFmpeg composition worker | Python rendering suggestion needed | 🟡 FFmpeg is the right tool; Python integration pattern not specified |
| **Frontend** | React + TypeScript + Vite + Tailwind | React (confirmed) | ✅ Aligned |
| **Backend** | FastAPI + Celery + Redis | Python FastAPI (confirmed) | ✅ Aligned |
| **Database** | PostgreSQL | PostgreSQL (confirmed) | ✅ Aligned |
| **Message Queue** | Redis + Celery | Not explicitly revised | ✅ Aligned (suggest RabbitMQ as an option) |

---

## 3. Documentation Files Requiring Updates

### 3.1 Architecture Documents

#### 🔴 [05-job-orchestration-and-render-pipeline.md](file:///f:/my-projects/reels-generation/docs/architecture/05-job-orchestration-and-render-pipeline.md)

**Updates needed:**
- **Add new pipeline stages:**
  - Stage 8a: "Start/End image prompt generation per scene"
  - Stage 8b: "End image generation with start-image reference"
  - Stage 8c: "Sequential reference chaining across scenes"
  - Stage 12a: "Audio stripping from generated video clips"
  - Stage 12b: "Clip speed-matching / time-stretching to narration duration"
- **Update render step model:** Each scene now has TWO image generation steps (start + end) instead of one keyframe
- **Update state machine:** Add `generating_image_pairs` state between scene planning and video generation
- **Update the dependency graph:** Image generation becomes sequential (scene N depends on scene N-1), not parallel
- **Update duration estimation:** 1–2 minute target instead of 30–60 seconds changes scene count calculations
- **Add speed-matching step:** Document `atempo` FFmpeg filter or `rubberband` for audio-accurate speed adjustment

---

#### 🔴 [06-provider-abstraction-and-integration-architecture.md](file:///f:/my-projects/reels-generation/docs/architecture/06-provider-abstraction-and-integration-architecture.md)

**Updates needed:**
- **Add concrete provider adapter specifications:**
  - `AzureOpenAIImageProvider` — Azure OpenAI DALL-E adapter
  - `BananaImageProvider` — Banana/nano-banana serverless GPU adapter
  - `Veo3VideoProvider` — Google Veo3 API adapter (start+end image to video interpolation)
  - `AzureOpenAISpeechProvider` — Azure OpenAI TTS adapter
  - `OpenSourceImageProvider` — interface for self-hosted models (FLUX, Stable Diffusion)
  - `OpenSourceVideoProvider` — interface for self-hosted models (Wan2.1, CogVideoX)
  - `OpenSourceTTSProvider` — interface for self-hosted TTS (XTTSv2, CosyVoice, Kokoro)
- **Add provider selection matrix:** Which provider for which modality, cost tier, and quality tier
- **Add Veo3-specific documentation:** Veo3 supports start+end frame interpolation — this is critical to the revised workflow
- **Document open-source model hosting:** Local inference via Docker containers, GPU requirements

---

#### 🔴 [04-data-model-and-storage.md](file:///f:/my-projects/reels-generation/docs/architecture/04-data-model-and-storage.md)

**Updates needed:**
- **Update `assets` table:** Add `asset_type` values: `start_image`, `end_image` (or update `image` to support sub-types with a `frame_position` field)
- **Update `scene_segments`:** Add fields for `start_image_prompt`, `end_image_prompt`, `start_image_asset_id`, `end_image_asset_id`
- **Update `render_steps`:** The step model needs to support paired image generation (start + end) as one logical step with two outputs
- **Update S3 layout:** Replace generic `images/` with `images/start/` and `images/end/` (or use naming convention)
- **Add MinIO section:** Document MinIO as the S3-compatible storage backend, including bucket configuration, access policies, and local development setup
- **Add `stripped_audio/` to storage layout:** Location for extracted audio from generated videos

---

#### 🟠 [08-visual-consistency-and-asset-memory.md](file:///f:/my-projects/reels-generation/docs/architecture/08-visual-consistency-and-asset-memory.md)

**Updates needed:**
- **Add sequential reference chaining model:** The end image of scene N becomes the start reference for scene N+1
- **Update consistency pack:** Add `previous_scene_end_image` as a required input for image generation (except scene 1)
- **Update prompt construction order:** Insert "reference to previous scene's end frame" into the prompt assembly order
- **Revise image generation flow diagram:** Show the linear dependency chain instead of parallel per-scene generation
- **Impact on parallelism:** Document that image generation is now **sequential by design**, which significantly impacts render time. Suggest batch-of-2 parallelism where possible (generate scene N's end image and scene N+1's start image in parallel using the same reference)

---

#### 🟠 [14-composition-and-av-consistency.md](file:///f:/my-projects/reels-generation/docs/architecture/14-composition-and-av-consistency.md)

**Updates needed:**
- **Add audio stripping pre-step:** Before composition, all generated video clips must have their audio tracks stripped (or muted). Document the FFmpeg command: `ffmpeg -i input.mp4 -an -c:v copy output_silent.mp4`
- **Add time-stretching step:** Document clip speed adjustment using FFmpeg `setpts` filter for video and `atempo` for audio, or MoviePy `speedx()`. Define tolerance rules (e.g., max 1.5× speed up, max 0.7× slow down)
- **Update duration sync section:** Current doc only covers freeze-frame pad and trim. Add speed-matching as a third option between trim and pad
- **Update pre-composition validation:** Add a check that all video clips have been audio-stripped

---

#### 🟠 [01-system-context.md](file:///f:/my-projects/reels-generation/docs/architecture/01-system-context.md)

**Updates needed:**
- **Add MinIO** to the system context diagram as the object storage backend (replacing generic "Object Storage / S3")
- **Add Docker** to the deployment units and diagram
- **Add specific provider names** to the "Generation Providers" node (Azure OpenAI, Veo3, Banana, open-source models)
- **Add message queue options:** Consider adding RabbitMQ as an alternative to Redis for Celery broker at scale

---

#### 🟠 [07-deployment-observability-and-security.md](file:///f:/my-projects/reels-generation/docs/architecture/07-deployment-observability-and-security.md)

**Updates needed:**
- **Add full Docker containerization strategy:**
  - Dockerfile specifications for: API service, Celery workers, FFmpeg composition workers, frontend build
  - Docker Compose for local development (including MinIO, PostgreSQL, Redis)
  - Production container orchestration guidance (Docker Swarm or Kubernetes)
  - GPU-enabled containers for local open-source model inference
- **Add MinIO deployment configuration:**
  - Bucket creation, access policies, lifecycle rules
  - MinIO Console access for development
  - MinIO client (mc) commands for operations
- **Update deployment units table** with container image names and GPU requirements

---

#### 🟡 [02-react-frontend-architecture.md](file:///f:/my-projects/reels-generation/docs/architecture/02-react-frontend-architecture.md)

**Updates needed:**
- **Add image pair review UI:** The keyframe review step now shows start+end image pairs, not single keyframes
- **Add speed-matching preview:** Allow users to preview speed-adjusted clips before final composition
- **Add viral idea selection UI:** Step 0 requires an idea browsing and selection interface
- **Update route map:** Add `/app/projects/:projectId/ideas` for idea selection

---

#### 🟡 [03-fastapi-backend-architecture.md](file:///f:/my-projects/reels-generation/docs/architecture/03-fastapi-backend-architecture.md)

**Updates needed:**
- **Add new worker types:**
  - Audio stripping worker
  - Speed-matching worker (or add to composition worker responsibilities)
  - Start/end image prompt generation worker
- **Update worker service list** to reflect the new pipeline stages
- **Add MinIO client configuration** in the integrations layer

---

### 3.2 Core Documents

#### 🟠 [01-project-overview.md](file:///f:/my-projects/reels-generation/docs/01-project-overview.md)

**Updates needed:**
- **Update "Product Promise" section:** Step 3 should mention "Generate start and end image prompts per scene" instead of "Build a scene plan"
- **Update video duration target:** 1–2 minutes instead of 30–60 seconds
- **Add "viral idea generation" concept** to the Core Workflows → Creator Workflow
- **Update System Components** to list MinIO, Docker, specific providers

---

#### 🟡 [02-roadmap-and-phase-index.md](file:///f:/my-projects/reels-generation/docs/02-roadmap-and-phase-index.md)

**Updates needed:**
- **Revise Phase 3 scope:** Include audio stripping, speed-matching, and image-pair generation
- **Consider adding a "Phase 2.5" or expanding Phase 2** to include start/end image prompt generation as part of content planning

---

### 3.3 Phase Documents

#### 🔴 Phase 3 (Render MVP) — All 4 files need updates

- [01-overview.md](file:///f:/my-projects/reels-generation/docs/phases/phase-3-render-mvp/01-overview.md): Add image pair generation, audio stripping, speed-matching to scope
- [02-architecture.md](file:///f:/my-projects/reels-generation/docs/phases/phase-3-render-mvp/02-architecture.md): Update render pipeline architecture for sequential image generation
- [03-implementation-plan.md](file:///f:/my-projects/reels-generation/docs/phases/phase-3-render-mvp/03-implementation-plan.md): Add implementation tasks for new steps
- [04-integrations.md](file:///f:/my-projects/reels-generation/docs/phases/phase-3-render-mvp/04-integrations.md): **Add concrete provider integrations:** Azure OpenAI, Veo3, Banana, open-source model adapters

#### 🟠 Phase 1 (Foundation) — Minor updates

- Update script duration target from 30–60s to 1–2 min
- Add "viral idea generation" with selection as a distinct feature
- Add MinIO and Docker to infrastructure setup deliverables

### 3.4 Appendices

#### 🟠 [01-api-surface-and-endpoint-catalog.md](file:///f:/my-projects/reels-generation/docs/appendices/01-api-surface-and-endpoint-catalog.md)

**Updates needed:**
- Add endpoints for idea selection: `POST /api/v1/projects/{project_id}/ideas/{idea_id}:select`
- Add endpoints for image-pair management per scene
- Add endpoint for audio strip status per clip

#### 🟠 [02-domain-glossary.md](file:///f:/my-projects/reels-generation/docs/appendices/02-domain-glossary.md)

**Updates needed:**
- Add: `Start Image`, `End Image`, `Image Pair`, `Reference Chaining`, `Audio Stripping`, `Speed Matching`, `Time Stretching`, `Viral Idea Pool`
- Update: `Keyframe` definition to account for start/end image pairs

#### 🟡 [03-risk-register.md](file:///f:/my-projects/reels-generation/docs/appendices/03-risk-register.md)

**Updates needed:**
- Add risk: "Sequential image generation increases total render time linearly with scene count"
- Add risk: "Speed-matching artifacts — excessive speed changes (>1.5×) produce unnatural video"
- Add risk: "Veo3 API availability and rate limits — single-provider dependency for video interpolation"

#### 🟡 [04-decision-log.md](file:///f:/my-projects/reels-generation/docs/appendices/04-decision-log.md)

**Updates needed:**
- Log decision: "Image generation uses start+end frame pairs with sequential reference chaining"
- Log decision: "MinIO replaces generic S3-compatible storage"
- Log decision: "Docker is the primary containerization platform"
- Log decision: "Azure OpenAI, Veo3, and Banana are the primary hosted providers"
- Log decision: "Audio stripping step added before composition"
- Log decision: "Speed-matching (time-stretch) replaces trim-only for duration sync"

---

## 4. Missing Documentation (New Documents Needed)

### 🔴 [NEW] `architecture/15-containerization-and-docker-strategy.md`

**Content:**
- Dockerfile specifications for each service (API, workers, frontend, composition)
- Docker Compose for local development (MinIO, PostgreSQL, Redis, API, workers)
- GPU-enabled container configuration for open-source model inference
- Production container orchestration (Docker Swarm / Kubernetes path)
- Image registry and CI/CD pipeline for container builds
- Volume mount strategy for model weights and asset storage
- Health check configuration for each container

### 🔴 [NEW] `architecture/16-minio-storage-configuration.md`

**Content:**
- MinIO deployment (single-node dev, distributed production)
- Bucket design: raw assets, exports, quarantine, model weights
- Access policies and IAM configuration
- Lifecycle rules for asset retention
- Pre-signed URL configuration (compatibility with S3 SDK)
- MinIO Console setup for development
- Backup and replication strategy
- Migration path from MinIO to cloud S3 if needed

### 🟠 [NEW] `architecture/17-concrete-provider-catalog.md`

**Content:**
- **Azure OpenAI:** Image generation (DALL-E), TTS, text generation — endpoints, auth, rate limits, cost per call
- **Banana (nano banana):** Serverless GPU inference — endpoint config, model deployment, cold start handling
- **Veo3 API:** Video generation with start+end frame interpolation — API contract, auth, output format, limitations
- **Open-source image models:** FLUX, Stable Diffusion — Docker container setup, GPU requirements, inference speed
- **Open-source video models:** Wan2.1, CogVideoX — Docker container setup, GPU requirements, I2V support
- **Open-source TTS:** XTTSv2, CosyVoice, Kokoro — Docker setup, voice cloning, multi-language support
- **Open-source music:** ACE-Step, Stable Audio — Docker setup, generation parameters
- Provider comparison matrix (quality, cost, speed, reliability)

### 🟡 [NEW] `docs/architecture/18-video-editing-and-rendering-tooling.md`

**Content — Python video editing libraries recommendation:**

| Library | Use Case | Pros | Cons |
|---|---|---|---|
| **FFmpeg** (via subprocess) | Core composition, encoding, audio stripping | Industry standard, fastest, most reliable | Not Pythonic, complex filter graphs |
| **MoviePy** | High-level video editing, speed changes, concatenation | Python-native, easy API, good for prototyping | Slower than raw FFmpeg, memory-heavy for long videos |
| **PyDub** | Audio manipulation (muting, speed, volume) | Simple API for audio-specific work | Audio only |
| **ffmpeg-python** | Pythonic FFmpeg wrapper | Clean API, builds FFmpeg commands from Python | Thin wrapper, still needs FFmpeg knowledge |
| **OpenCV** | Frame-level video processing | Precise frame control | Not designed for A/V composition |

**Recommendation:** Use `ffmpeg-python` as the primary wrapper for composition commands, `PyDub` for audio preprocessing (stripping, speed-matching), and raw FFmpeg for the final render. MoviePy for development/prototyping only.

---

## 5. Suggested Additional Services

Based on the revised requirements, consider adding:

| Service | Purpose | Priority |
|---|---|---|
| **RabbitMQ** | More robust message broker than Redis for production Celery (supports priority queues, message persistence) | 🟡 Medium |
| **Prometheus + Grafana** | Metrics and dashboards for queue depth, provider latency, render SLOs | 🟡 Medium |
| **Nginx / Traefik** | Reverse proxy, TLS termination, load balancing (mentioned in docs but not containerized) | 🟠 High |
| **pgAdmin** | PostgreSQL management UI for development | 🟢 Low |
| **Redis Commander** | Redis monitoring UI for development | 🟢 Low |
| **GPU Worker Container** | Dedicated Docker container with CUDA + model weights for local inference | 🔴 Critical |
| **Model Weight Volume** | Shared Docker volume or MinIO bucket for model weights | 🟠 High |

---

## 6. Priority-Ordered Update Plan

### Phase A — Critical Updates (Do First)

1. Update [05-job-orchestration-and-render-pipeline.md](file:///f:/my-projects/reels-generation/docs/architecture/05-job-orchestration-and-render-pipeline.md) — new pipeline stages for image pairs, audio stripping, speed-matching
2. Update [04-data-model-and-storage.md](file:///f:/my-projects/reels-generation/docs/architecture/04-data-model-and-storage.md) — new asset types, scene segment fields, MinIO storage
3. Update [08-visual-consistency-and-asset-memory.md](file:///f:/my-projects/reels-generation/docs/architecture/08-visual-consistency-and-asset-memory.md) — sequential reference chaining model
4. Create [NEW] `15-containerization-and-docker-strategy.md`
5. Create [NEW] `16-minio-storage-configuration.md`

### Phase B — High Priority Updates

6. Update [06-provider-abstraction-and-integration-architecture.md](file:///f:/my-projects/reels-generation/docs/architecture/06-provider-abstraction-and-integration-architecture.md) — concrete provider adapters
7. Create [NEW] `17-concrete-provider-catalog.md`
8. Update [14-composition-and-av-consistency.md](file:///f:/my-projects/reels-generation/docs/architecture/14-composition-and-av-consistency.md) — audio stripping, speed-matching
9. Update all Phase 3 docs (4 files)
10. Update [07-deployment-observability-and-security.md](file:///f:/my-projects/reels-generation/docs/architecture/07-deployment-observability-and-security.md) — Docker, MinIO

### Phase C — Medium Priority Updates

11. Update [01-project-overview.md](file:///f:/my-projects/reels-generation/docs/01-project-overview.md) — viral ideas, 1–2 min duration
12. Update [01-system-context.md](file:///f:/my-projects/reels-generation/docs/architecture/01-system-context.md) — diagram updates
13. Update all 4 appendices
14. Create [NEW] `18-video-editing-and-rendering-tooling.md`
15. Update Phase 1 docs

### Phase D — Lower Priority

16. Update frontend and backend architecture docs
17. Update remaining phase docs (2, 4–7)
18. Update README.md with new document links

---

## 7. Key Architectural Impact of Revised Workflow

> [!CAUTION]
> The most impactful change is the shift from **parallel per-scene image generation** to **sequential reference-chained image generation**. This fundamentally changes render time from `O(1)` (all scenes in parallel) to `O(n)` (linear in scene count). For a 1–2 minute video with 12–24 sub-scripts, this could mean 12–24× longer image generation time if done purely sequentially.

### Mitigation Strategies to Document

1. **Pipelining:** Start video generation for scene N as soon as scene N's images are done, while scene N+1's images generate
2. **Batch-of-2 parallelism:** Generate scene N's end image and scene N+1's start image concurrently (both reference scene N's start image)
3. **User-driven checkpoints:** Let users approve batches of 4–5 scenes at a time while later scenes generate
4. **Cached reference reuse:** If the same consistency pack + style produces similar starts, allow reuse across similar scenes

> [!IMPORTANT]
> The **Veo3 start+end frame interpolation** model is the key enabler for the revised workflow. If Veo3 is unavailable or doesn't support this mode, the fallback strategy (single keyframe → image-to-video) must be clearly documented as a degraded mode.
