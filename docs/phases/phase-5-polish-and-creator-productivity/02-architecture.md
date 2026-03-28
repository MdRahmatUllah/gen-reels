# Phase 5 Architecture

## Components Added

- Template service and cloning engine
- Asset library views and search
- Subtitle styling and export refinement logic
- Prompt history lineage views
- Audio polish utilities
- Music provider adapter for AI-generated tracks
- Social publish integration stub

## Data Changes

- Add `project_templates` and `template_versions` records
- Extend `assets` and `exports` with library metadata and reuse markers
- Store prompt history and lineage references from generated outputs back to approved inputs
- Track continuity-score metadata and reusable frame-pair lineage

## Risk Controls

- Reuse features must preserve lineage so creators understand what was copied and what was regenerated.
- Template cloning must strip workspace-specific secrets and preset references that are not transferable.
- Shared frame-pair reuse must never silently break continuity-chain assumptions in a new project.
