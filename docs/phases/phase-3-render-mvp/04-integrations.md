# Phase 3 Integrations

## External Integrations

- Hosted image generation providers through adapters
- Hosted video generation provider with first/last-frame support where available
- Hosted speech or TTS provider
- Curated royalty-free music library
- Moderation provider for output safety checks

## Internal Platform Integrations

- PostgreSQL for render, asset, export, and consistency-pack snapshot state
- Redis/Celery for queue orchestration
- MinIO-backed object storage for raw and final media assets
- FFmpeg for silent-clip normalization, retiming, and composition
- SSE for render progress updates

## Contract Requirements

- Every modality adapter must return normalized metadata and a durable output reference.
- Render orchestration must be able to retry a single scene step with no schema ambiguity.
- Video adapters must declare whether they support first/last-frame generation or only single-image I2V.
- Output moderation must run on generated frame pairs and video clips before those assets advance downstream.

## Error Strategy

- Classify failures into retryable provider errors, deterministic input errors, moderation rejections, and composition errors.
- Keep failed assets and provider metadata for operator review.
- Do not attempt invisible cross-provider fallback for user-visible media outputs in the MVP.
