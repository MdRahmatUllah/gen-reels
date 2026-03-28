# Phase 3 Integrations

## External Integrations

- Primary image generation provider
- Primary video generation provider (image-to-video mode preferred)
- Primary speech or TTS provider
- Curated royalty-free music library (bundled with the platform — no external API required for Phase 3 music). Music generation via external provider is deferred to Phase 5.
- Moderation provider for output safety checks

## Internal Platform Integrations

- PostgreSQL for render, asset, export, and consistency pack snapshot state
- Redis/Celery for queue orchestration
- Object storage for raw and final media assets
- FFmpeg for composition
- SSE for render progress updates with polling fallback
- Consistency pack and keyframe review data from planning layers

## Contract Requirements

- Every modality adapter must return normalized metadata and a durable output reference (asset storage key).
- Render orchestration must be able to retry a single scene step with no schema ambiguity.
- Composition inputs must be generated from stored asset references, not in-memory worker state.
- Consistency pack must be resolved and snapshotted at render job creation. Workers receive the snapshot ID, not the live consistency pack.
- Image-to-video adapters must accept a reference image asset key as an optional input; text-to-video is used only as a fallback when no approved keyframe exists.
- Output moderation must run on generated images and video clips before those assets advance to approval or composition.

## Error Strategy

- Classify failures into retryable provider errors, deterministic input errors, moderation rejections, and composition errors.
- Keep failed assets and provider metadata for operator review.
- Do not attempt invisible cross-provider fallback for user-visible media outputs in the MVP.
- Moderation rejections are non-retryable and must surface to the user with a scene-level error.

## Cost Notes

- This is the first phase where unit economics can break the product if not measured.
- Capture provider cost, duration, and success rate from the first render in staging and production before production launch.
- Music from a curated library has zero marginal generation cost in Phase 3, which improves gross margin visibility for the video and narration generation cost centers.
- Preview renders should record the same usage units as full renders, even though customer-visible credit enforcement begins in Phase 4.

