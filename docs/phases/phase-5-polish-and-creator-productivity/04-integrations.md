# Phase 5 Integrations

## External Integrations

- Optional subtitle timing or transcription provider if needed
- Optional music provider or curated music source

## Internal Platform Integrations

- Asset and export records
- FFmpeg composition settings
- Existing preset and project models

## Contract Requirements

- Template cloning must preserve allowed references and remove forbidden workspace-specific secrets.
- Subtitle styling must map to deterministic export settings.
- Music handling must clearly distinguish generated tracks from curated tracks.

## Error Strategy

- Missing or expired source assets should block reuse with a clear error.
- Subtitle generation fallback must not silently desync the final export.
- Audio polish should fail safely and preserve a basic usable export path.

## Cost Notes

- This phase should improve retention and workflow speed more than direct generation quality.
- If generative music is added here, cost must be compared against simpler curated-track alternatives.

