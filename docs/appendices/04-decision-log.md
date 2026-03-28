# Decision Log

## Current Decisions

### Product Scope

- Build a creator-first product first, even though the longer-term architecture supports agencies and studio teams.
- Use a phased rollout rather than trying to ship the broadest platform on day one.
- The canonical creator workflow includes idea selection before script generation.
- Launch target duration is 60-120 seconds with 5-8 second scene segments.

### Frontend

- Use React with TypeScript and Vite for a clean separation from the FastAPI backend.
- Build the app around long-lived project workflows rather than isolated modal tools.
- Use SSE for render progress updates with a polling fallback.

### Backend

- Use FastAPI with async job orchestration rather than a synchronous API that waits on generation.
- Use PostgreSQL as the system of record and MinIO-backed S3-compatible storage for assets.
- Use the cloud provider's native secret manager for secret storage.
- Route handlers delegate to one service method.

### Orchestration

- Model rendering as checkpointed steps with resumability and scene-level retries.
- Planning jobs and render jobs share the same `render_jobs` and `render_steps` schema family.
- A frame-pair review gate is inserted between frame generation and video generation.
- Scene continuity is enforced through a chained frame model where later scenes may depend on the previous scene's approved end frame.

### Consistency And Asset Memory

- Visual continuity is a platform-level concern enforced through the consistency pack system plus chained continuity anchors.
- Every image and video generation call must have a resolved consistency pack before dispatch.
- Providers with first/last-frame video support are preferred over single-image I2V for the canonical path.

### Commercial

- Meter rendering through credits or usage-based controls.
- Credit balances are always computed from the ledger.
- Frame-pair image generation is billed as a distinct scene-level unit.

### Audio And Composition

- Provider-returned clip audio is not part of the default final mix.
- If the provider supports silent output, request it; otherwise strip clip audio after generation.
- Clip retiming uses bounded speed adjustment first, then freeze-pad or trim if needed.
- Final export audio is normalised to -14 LUFS integrated with -1.0 dBTP true peak limit.
- Background music attenuates by -12 dB during narration sections with a 0.3 second fade.
- All narration steps within a render job must use the same `voice_preset_id`.

### Provider Reference Stack

- Azure OpenAI is the reference hosted text and narration provider.
- Azure OpenAI plus Gemini 2.5 Flash Image ("nano banana") are the reference hosted image providers.
- Veo 3.1 class provider is the reference hosted video provider.
- Open-source image, video, and TTS providers remain supported through adapter contracts and later BYO/local execution.

## Deferred Decisions

- Exact billing vendor choice
- Exact cloud deployment target
- Which open-source image models move from experimental to supported
- Whether scene preview renders return before the full scene chain is complete
