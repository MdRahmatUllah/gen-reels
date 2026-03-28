# Decision Log

## Current Decisions

### Product Scope

- Build a creator-first product first, even though the longer-term architecture supports agencies and studio teams.
- Use a phased rollout rather than trying to ship the broadest platform on day one.

### Frontend

- Use React with TypeScript and Vite for a clean separation from the FastAPI backend.
- Build the app around long-lived project workflows rather than isolated modal tools.
- Use SSE for render progress updates with a polling fallback (3 failed reconnects trigger polling at 5-second intervals). No separate polling endpoint is introduced.

### Backend

- Use FastAPI with async job orchestration rather than a synchronous API that waits on generation.
- Use PostgreSQL as the system of record and S3-compatible storage for assets.
- Use the cloud provider's native secret manager for secret storage. No plaintext secrets in environment variables in staging or production.
- Route handler rule: route handlers delegate to one service method. Business logic may not live in route handlers.
- Database session rule: API requests use async per-request sessions via FastAPI `Depends`. Celery workers manage sync sessions directly. Workers do not use FastAPI session injection.

### Orchestration

- Model rendering as checkpointed steps with resumability and scene-level retries.
- Keep workers and providers behind stable interfaces.
- Job schema for render steps is defined in Phase 1 even if only planning tasks use it. Planning jobs and render jobs share the same `render_jobs` / `render_steps` schema, differentiated by job type.
- A keyframe review gate is inserted between image generation and video generation. Users approve or regenerate keyframes before video generation consumes them.

### Consistency And Asset Memory

- Visual consistency is a platform-level concern enforced through the consistency pack system, not a prompt engineering concern left to creators.
- Every image and video generation call must have a resolved consistency pack before dispatch.
- Image-to-video is preferred over text-to-video whenever an approved keyframe exists for a scene.

### Commercial

- Meter rendering through credits or usage-based controls.
- Treat reliability and billing as phase-4 requirements, not late-stage polish.
- Credit balances are always computed from the ledger. No denormalized balance column.

### Music Strategy (Phase 3)

- Phase 3 Render MVP uses a **curated royalty-free music library** as the default music source. Users select from a bundled track set.
- Generated music (AI-generated tracks) is introduced in Phase 5 as an optional modality.
- Uploaded custom tracks (BYO music) are introduced in Phase 5 alongside the template library.
- This decision resolves the deferred item from the original decision log.

### Preview Render (Phase 3)

- Phase 3 includes a **single-scene preview render** mode. Users can trigger a full pipeline run (image generation + video generation + narration) on one selected scene before committing to a full render job.
- Preview renders record the same usage units that later map to production credit costs, but customer-visible credit reservation and enforcement begin in Phase 4.
- Preview renders produce exportable assets that can be promoted into a full render job.

### Subtitles And Export Behavior

- Subtitle generation ships in Phase 3 as a non-blocking export step: if subtitle generation fails, the export can still complete.
- Subtitle styling and richer subtitle controls are deferred to Phase 5.

### Safety And Policy

- Input moderation begins in Phase 1 and output moderation begins in Phase 3. Platform-level moderation is mandatory even if providers expose their own safety filters.
- Workspace API keys and local worker registration tokens are separate credential types with different scopes and rotation rules.
- Moderation text classification results are cached in Redis keyed by `(text_hash, provider_version)` with a 24-hour TTL. Image moderation results are not cached because generated image output is always unique.

### Template And Asset Portability

- When a project template is cloned into a new project, character sheet and style descriptor text fields are copied. Reference keyframe images are **not** carried over — they are workspace-scoped and not portable between projects. The cloned project starts with a text-only consistency pack that users populate during Phase 2 for the new project.

### Keyframe Review Timeout

- The keyframe review timeout is 7 days. The platform must send a reminder notification at T-24 hours and T-48 hours before the timeout expires. If the timeout is reached without action, the job transitions to `failed` with reason `keyframe_review_timeout`.

### Composition And Audio-Visual Consistency (Phase 3)

- All scene clips in a render job are assembled by the composition worker into a single export. The composition step runs only after all required assets are in `completed` state.
- **Loudness target:** Final export audio is normalised to −14 LUFS integrated with −1.0 dBTP true peak limit (TikTok and Instagram Reels standard).
- **Music ducking:** Background music attenuates by −12 dB during narration sections with a 0.3-second fade to avoid audio pumping.
- **Voice continuity:** All narration steps within a render job must use the same `voice_preset_id`, frozen at render job creation. Per-scene voice overrides are not supported in Phases 3–4.
- **Scene transition default:** `hard_cut`. Crossfade (0.25–0.5 s dissolve) becomes configurable via visual preset in Phase 5.
- **Duration sync:** If narration audio is longer than the video clip, the clip is freeze-frame padded. If the clip is more than 3 seconds longer than narration, it is trimmed.
- **Consistency provenance check:** The composition worker confirms all scene clips reference the same `consistency_pack_snapshot_id` as the render job. A mismatch fails composition — the platform will never silently deliver a visually inconsistent export.

## Deferred Decisions

- Exact provider vendors per modality (image, video, narration, music)
- Payment vendor choice (Stripe is the assumed default but not formally decided)
- SSO vendor for Phase 6 enterprise tier
- Whether social publishing (TikTok, Instagram) ships in Phase 5 or Phase 6

## Decision Update Rule

Whenever a decision materially changes architecture, schema, queue behavior, or pricing assumptions, update this file and the relevant architecture or phase document in the same change.
