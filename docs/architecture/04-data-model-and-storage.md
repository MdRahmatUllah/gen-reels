# Data Model And Storage

## Data Storage Strategy

- PostgreSQL stores structured product data, workflow state, usage records, and references to media assets.
- MinIO-backed S3-compatible object storage stores raw generation assets, intermediate outputs, composed exports, subtitles, and prompt-related artifacts when needed.
- Redis stores transient queue and cache state only; it is not a system of record.

## Core Entities

### Identity And Commercial

- `users`
- `sessions`
- `workspaces`
- `workspace_members`
- `plans`
- `subscriptions`
- `credit_ledger_entries`

### Production Workflow

- `projects`
- `project_briefs`
- `idea_sets`
- `script_versions`
- `scene_plans`
- `scene_segments`
- `visual_presets`
- `voice_presets`
- `brand_kits`
- `consistency_packs`
- `project_templates`
- `template_versions`
- `review_requests`
- `comments`

### Generation And Assets

- `render_jobs`
- `render_steps`
- `provider_runs`
- `assets`
- `asset_variants`
- `exports`

### Operations And Compliance

- `audit_events`
- `moderation_events`
- `moderation_reports`
- `notification_events`
- `notification_preferences`
- `webhook_endpoints`
- `webhook_deliveries`
- `workspace_api_keys`
- `social_publish_targets`
- `worker_registrations`

## Recommended Entity Relationships

- A workspace has many projects.
- A project has many idea sets, script versions, and scene plans.
- A project stores one selected idea at a time as the active concept for script generation.
- A project has one active consistency pack; consistency packs are versioned alongside scene plans.
- A scene plan has many ordered scene segments.
- Each scene segment stores a `start_image_prompt` and `end_image_prompt`.
- A render job points to one approved script version and one approved scene plan.
- A render job has many render steps and many generated assets.
- Provider runs attach to render steps and asset generation attempts.
- Exports belong to projects and optionally to specific render jobs.
- Project templates are workspace-owned and may be cloned into new projects.

## Asset Type Discriminator

All generated and composed media objects are stored as `assets` rows. The `asset_type` column is a required discriminator:

| `asset_type` value | Description |
| --- | --- |
| `image` | Generated scene still image |
| `video_clip` | Generated scene video clip |
| `narration` | Generated TTS audio for a scene |
| `music` | Background music track |
| `subtitle` | Subtitle or caption file |
| `export` | Final composed reel export |
| `reference_image` | User-uploaded or approved continuity reference |
| `upload` | User-submitted media file |

### Asset Role Metadata

Image assets require an additional `asset_role` metadata field:

| `asset_role` value | Description |
| --- | --- |
| `scene_start_frame` | Approved start frame for a scene |
| `scene_end_frame` | Approved end frame for a scene |
| `continuity_anchor` | End frame reused as the next scene's chain input |

Video clip assets require:

- `has_audio_stream` boolean
- `source_audio_policy` enum: `request_silent`, `strip_after_generation`, `preserve`
- `timing_alignment_strategy` enum: `none`, `speed_adjust`, `freeze_pad`, `trim`

## Versioning Rules

- Briefs, scripts, and scene plans must support draft and approved versions.
- A render job always points to immutable approved inputs.
- Asset retries create new variants instead of replacing historical records.
- Final export records should preserve the exact inputs and provider runs used to create them.
- Consistency packs are versioned and snapshotted when a scene plan is approved.

## Scene Segment Fields

Each `scene_segment` should include:

- `scene_index`
- `narration_text`
- `visual_prompt`
- `start_image_prompt`
- `end_image_prompt`
- `target_duration_seconds`
- `estimated_voice_duration_seconds`
- `actual_voice_duration_seconds`
- `chain_parent_asset_id` nullable

## Asset Storage Layout

```text
workspace/{workspace_id}/project/{project_id}/
  briefs/
  scripts/
  scenes/
  consistency/
    pack.json
    reference_images/
    character_sheets/
  assets/
    images/
      start/
      end/
    videos/
      raw/
      silent/
      retimed/
    audio/
      narration/
    music/
    subtitles/
    uploads/
  exports/
  quarantine/
```

## Asset States

- `queued`
- `running`
- `completed`
- `failed`
- `expired`
- `superseded`
- `quarantined`

## Retention Strategy

- Keep final exports and approved planning inputs longer than intermediate assets.
- Preserve provider run metadata even if raw assets are later archived.
- Define retention windows by plan tier and workspace policy in later phases.
- Quarantined moderation assets are retained for a minimum of 90 days independent of other retention policies.

## Data Integrity Considerations

- Use database constraints for ordering, ownership, and valid state transitions where practical.
- Prefer soft deletion or archival over hard deletion for audit-sensitive records.
- Record prompt versions, provider parameters, reference asset IDs, and cost metadata together with each provider run.
- Credit ledger entries are immutable.
- Workspace API keys are hash-stored and never recoverable after creation.
- Review requests, moderation decisions, and webhook deliveries should be auditable and append-only where possible.
