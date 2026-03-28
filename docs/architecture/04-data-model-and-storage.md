# Data Model And Storage

## Data Storage Strategy

- PostgreSQL stores structured product data, workflow state, usage records, and references to media assets.
- S3-compatible object storage stores raw generation assets, intermediate outputs, composed exports, subtitles, and prompt-related artifacts when needed.
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
- `social_publish_targets` (Phase 5)
- `worker_registrations` (Phase 7)

## Recommended Entity Relationships

- A workspace has many projects.
- A project has many script versions and scene plans.
- A project has one active consistency pack; consistency packs are versioned alongside scene plans.
- A scene plan has many ordered scene segments.
- A render job points to one approved script version and one approved scene plan.
- A render job has many render steps and many generated assets.
- Provider runs attach to render steps and asset generation attempts.
- Exports belong to projects and optionally to specific render jobs.
- Project templates are workspace-owned and may be cloned into new projects.
- Review requests and comments attach to workspace-owned project artifacts such as scene plans, exports, or templates.
- Webhook endpoints and workspace API keys belong to a workspace and are managed by workspace admins.
- Worker registrations belong to a workspace and store capability metadata plus heartbeat state.
- Moderation reports attach to moderation events when users dispute a moderation outcome.

## Asset Type Discriminator

All generated and composed media objects are stored as `assets` rows. The `asset_type` column is a required discriminator:

| `asset_type` value | Description |
|---|---|
| `image` | Generated scene keyframe image |
| `video_clip` | Generated scene video clip |
| `narration` | Generated TTS audio for a scene |
| `music` | Background music track (generated or curated) |
| `subtitle` | Subtitle or caption file |
| `export` | Final composed reel export |
| `reference_image` | User-uploaded or approved consistency reference |
| `upload` | User-submitted media file |

## Versioning Rules

- Briefs, scripts, and scene plans must support draft and approved versions.
- A render job always points to immutable approved inputs.
- **Immutability rule:** Approved records cannot be edited. A user can create a new draft at any time, but a new draft only replaces the active approved version through an explicit re-approval action. Active render jobs are never retroactively affected by a new draft or new approval. Render jobs are permanently bound to the exact version IDs that existed when the job was created.
- Asset retries create new variants instead of replacing historical records.
- Final export records should preserve the exact inputs and provider runs used to create them.
- Consistency packs are versioned and snapshotted when a scene plan is approved.

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
    videos/
    audio/
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

## Project Lifecycle States

Projects support soft archival rather than hard deletion. The `projects` table includes:

- `archived_at` — timestamp when archived; null for active projects.
- `deleted_at` — timestamp for soft deletion; preserves audit records even if assets are cleaned up.

Archive behavior: archived projects are excluded from the project list by default but remain accessible via direct link or through a filter. Archived project assets follow the standard retention policy. Archival does not cancel active render jobs.

## Retention Strategy

- Keep final exports and approved planning inputs longer than intermediate assets.
- Preserve provider run metadata even if raw assets are later archived.
- Define retention windows by plan tier and workspace policy in later phases.
- Quarantined moderation assets are retained for a minimum of 90 days independent of other retention policies.

## Data Integrity Considerations

- Use database constraints for ordering, ownership, and valid state transitions where practical.
- Prefer soft deletion or archival over hard deletion for audit-sensitive records.
- Record prompt versions, provider parameters, and cost metadata together with each provider run.
- Credit ledger entries are immutable: corrections are recorded as new entries (credit, debit, or adjustment), never as updates to existing rows.
- Workspace API keys are hash-stored and never recoverable after creation.
- Review requests, moderation decisions, and webhook deliveries should be auditable and append-only where possible.

