# Phase 2 Integrations

## External Integrations

- Primary text generation provider for scene plan generation
- Optional timing assistance or speech estimation library if adopted

## Internal Platform Integrations

- PostgreSQL for scene, preset, and approval records
- Redis/Celery for async planning work
- Logging and metrics for planning quality and edit frequency

## Contract Requirements

- Scene planning input must include approved script content, brief context, and selected presets.
- Scene planning output must return ordered scene structures with narration text, visual prompt hints, and estimated duration.
- Presets should be platform-native records rather than provider-native blobs.

## Error Strategy

- If generated scene plans are malformed, fail the planning task with validation details.
- Scene plan generation should be repeatable without corrupting approved script state.
- Preset validation should happen before a scene plan is approved.

## Cost Notes

- Phase 2 still uses relatively low-cost text generation.
- Cost capture is important because this phase determines how often users regenerate planning outputs before rendering.

