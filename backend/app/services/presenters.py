from __future__ import annotations

from app.models.entities import (
    Asset,
    IdeaCandidate,
    IdeaSet,
    JobStatus,
    Project,
    ProjectBrief,
    RenderJob,
    RenderStep,
    ScenePlan,
    SceneSegment,
    ScriptVersion,
    VisualPreset,
    VoicePreset,
    ExportRecord,
)


def project_to_dict(project: Project) -> dict[str, object]:
    return {
        "id": project.id,
        "workspace_id": project.workspace_id,
        "owner_user_id": project.owner_user_id,
        "title": project.title,
        "client": project.client,
        "aspect_ratio": project.aspect_ratio,
        "duration_target_sec": project.duration_target_sec,
        "stage": project.stage.value,
        "active_brief_id": project.active_brief_id,
        "selected_idea_id": project.selected_idea_id,
        "active_script_version_id": project.active_script_version_id,
        "active_scene_plan_id": project.active_scene_plan_id,
        "default_visual_preset_id": project.default_visual_preset_id,
        "default_voice_preset_id": project.default_voice_preset_id,
        "archived_at": project.archived_at,
        "deleted_at": project.deleted_at,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def brief_to_dict(brief: ProjectBrief) -> dict[str, object]:
    return {
        "id": brief.id,
        "project_id": brief.project_id,
        "version_number": brief.version_number,
        "objective": brief.objective,
        "hook": brief.hook,
        "target_audience": brief.target_audience,
        "call_to_action": brief.call_to_action,
        "brand_north_star": brief.brand_north_star,
        "guardrails": brief.guardrails,
        "must_include": brief.must_include,
        "approval_steps": brief.approval_steps,
        "created_at": brief.created_at,
    }


def idea_candidate_to_dict(candidate: IdeaCandidate) -> dict[str, object]:
    return {
        "id": candidate.id,
        "idea_set_id": candidate.idea_set_id,
        "project_id": candidate.project_id,
        "title": candidate.title,
        "hook": candidate.hook,
        "summary": candidate.summary,
        "tags": candidate.tags,
        "order_index": candidate.order_index,
        "status": candidate.status.value,
        "created_at": candidate.created_at,
    }


def idea_set_to_dict(idea_set: IdeaSet, candidates: list[IdeaCandidate]) -> dict[str, object]:
    return {
        "id": idea_set.id,
        "project_id": idea_set.project_id,
        "source_brief_id": idea_set.source_brief_id,
        "created_at": idea_set.created_at,
        "candidates": [idea_candidate_to_dict(candidate) for candidate in candidates],
    }


def script_version_to_dict(script_version: ScriptVersion) -> dict[str, object]:
    return {
        "id": script_version.id,
        "project_id": script_version.project_id,
        "based_on_idea_id": script_version.based_on_idea_id,
        "parent_version_id": script_version.parent_version_id,
        "version_number": script_version.version_number,
        "source_type": script_version.source_type.value,
        "approval_state": script_version.approval_state,
        "approved_at": script_version.approved_at,
        "approved_by_user_id": script_version.approved_by_user_id,
        "total_words": script_version.total_words,
        "estimated_duration_seconds": script_version.estimated_duration_seconds,
        "reading_time_label": script_version.reading_time_label,
        "lines": script_version.lines,
        "created_at": script_version.created_at,
    }


def scene_segment_to_dict(scene_segment: SceneSegment) -> dict[str, object]:
    return {
        "id": scene_segment.id,
        "scene_plan_id": scene_segment.scene_plan_id,
        "scene_index": scene_segment.scene_index,
        "source_line_ids": scene_segment.source_line_ids,
        "title": scene_segment.title,
        "beat": scene_segment.beat,
        "narration_text": scene_segment.narration_text,
        "caption_text": scene_segment.caption_text,
        "visual_direction": scene_segment.visual_direction,
        "shot_type": scene_segment.shot_type,
        "motion": scene_segment.motion,
        "target_duration_seconds": scene_segment.target_duration_seconds,
        "estimated_voice_duration_seconds": scene_segment.estimated_voice_duration_seconds,
        "actual_voice_duration_seconds": scene_segment.actual_voice_duration_seconds,
        "visual_prompt": scene_segment.visual_prompt,
        "start_image_prompt": scene_segment.start_image_prompt,
        "end_image_prompt": scene_segment.end_image_prompt,
        "transition_mode": scene_segment.transition_mode,
        "notes": scene_segment.notes,
        "validation_warnings": scene_segment.validation_warnings,
        "chained_from_asset_id": scene_segment.chained_from_asset_id,
        "start_image_asset_id": scene_segment.start_image_asset_id,
        "end_image_asset_id": scene_segment.end_image_asset_id,
        "created_at": scene_segment.created_at,
        "updated_at": scene_segment.updated_at,
    }


def scene_plan_to_dict(scene_plan: ScenePlan, segments: list[SceneSegment]) -> dict[str, object]:
    return {
        "id": scene_plan.id,
        "project_id": scene_plan.project_id,
        "based_on_script_version_id": scene_plan.based_on_script_version_id,
        "created_by_user_id": scene_plan.created_by_user_id,
        "visual_preset_id": scene_plan.visual_preset_id,
        "voice_preset_id": scene_plan.voice_preset_id,
        "consistency_pack_id": scene_plan.consistency_pack_id,
        "parent_scene_plan_id": scene_plan.parent_scene_plan_id,
        "version_number": scene_plan.version_number,
        "source_type": scene_plan.source_type.value,
        "approval_state": scene_plan.approval_state,
        "approved_at": scene_plan.approved_at,
        "approved_by_user_id": scene_plan.approved_by_user_id,
        "total_estimated_duration_seconds": scene_plan.total_estimated_duration_seconds,
        "scene_count": scene_plan.scene_count,
        "validation_warnings": scene_plan.validation_warnings,
        "created_at": scene_plan.created_at,
        "updated_at": scene_plan.updated_at,
        "segments": [scene_segment_to_dict(segment) for segment in segments],
    }


def visual_preset_to_dict(preset: VisualPreset) -> dict[str, object]:
    return {
        "id": preset.id,
        "workspace_id": preset.workspace_id,
        "created_by_user_id": preset.created_by_user_id,
        "name": preset.name,
        "description": preset.description,
        "prompt_prefix": preset.prompt_prefix,
        "style_descriptor": preset.style_descriptor,
        "negative_prompt": preset.negative_prompt,
        "camera_defaults": preset.camera_defaults,
        "color_palette": preset.color_palette,
        "reference_notes": preset.reference_notes,
        "is_archived": preset.is_archived,
        "created_at": preset.created_at,
        "updated_at": preset.updated_at,
    }


def voice_preset_to_dict(preset: VoicePreset) -> dict[str, object]:
    return {
        "id": preset.id,
        "workspace_id": preset.workspace_id,
        "created_by_user_id": preset.created_by_user_id,
        "name": preset.name,
        "description": preset.description,
        "provider_voice": preset.provider_voice,
        "tone_descriptor": preset.tone_descriptor,
        "language_code": preset.language_code,
        "pace_multiplier": preset.pace_multiplier,
        "is_archived": preset.is_archived,
        "created_at": preset.created_at,
        "updated_at": preset.updated_at,
    }


def job_to_dict(job: RenderJob) -> dict[str, object]:
    return {
        "id": job.id,
        "workspace_id": job.workspace_id,
        "project_id": job.project_id,
        "created_by_user_id": job.created_by_user_id,
        "script_version_id": job.script_version_id,
        "scene_plan_id": job.scene_plan_id,
        "consistency_pack_id": job.consistency_pack_id,
        "voice_preset_id": job.voice_preset_id,
        "job_kind": job.job_kind.value,
        "queue_name": job.queue_name,
        "status": job.status.value if isinstance(job.status, JobStatus) else str(job.status),
        "idempotency_key": job.idempotency_key,
        "request_hash": job.request_hash,
        "payload": job.payload,
        "allow_export_without_music": job.allow_export_without_music,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "started_at": job.started_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at,
        "cancelled_at": job.cancelled_at,
    }


def render_step_to_dict(step: RenderStep) -> dict[str, object]:
    return {
        "id": step.id,
        "render_job_id": step.render_job_id,
        "project_id": step.project_id,
        "scene_segment_id": step.scene_segment_id,
        "step_kind": step.step_kind.value,
        "step_index": step.step_index,
        "status": step.status.value if isinstance(step.status, JobStatus) else str(step.status),
        "is_stale": step.is_stale,
        "retry_count": step.retry_count,
        "retry_history": step.retry_history,
        "recovery_source_step_id": step.recovery_source_step_id,
        "checkpoint_payload": step.checkpoint_payload,
        "last_checkpoint_at": step.last_checkpoint_at,
        "input_payload": step.input_payload,
        "output_payload": step.output_payload,
        "error_code": step.error_code,
        "error_message": step.error_message,
        "started_at": step.started_at,
        "completed_at": step.completed_at,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
    }


def asset_to_dict(asset: Asset, *, download_url: str | None = None) -> dict[str, object]:
    return {
        "id": asset.id,
        "workspace_id": asset.workspace_id,
        "project_id": asset.project_id,
        "render_job_id": asset.render_job_id,
        "render_step_id": asset.render_step_id,
        "scene_segment_id": asset.scene_segment_id,
        "parent_asset_id": asset.parent_asset_id,
        "provider_run_id": asset.provider_run_id,
        "consistency_pack_snapshot_id": asset.consistency_pack_snapshot_id,
        "asset_type": asset.asset_type.value,
        "asset_role": asset.asset_role.value,
        "status": asset.status,
        "bucket_name": asset.bucket_name,
        "object_name": asset.object_name,
        "file_name": asset.file_name,
        "content_type": asset.content_type,
        "size_bytes": asset.size_bytes,
        "duration_ms": asset.duration_ms,
        "width": asset.width,
        "height": asset.height,
        "frame_rate": asset.frame_rate,
        "quarantine_bucket_name": asset.quarantine_bucket_name,
        "quarantine_object_name": asset.quarantine_object_name,
        "quarantined_at": asset.quarantined_at,
        "released_at": asset.released_at,
        "has_audio_stream": asset.has_audio_stream,
        "source_audio_policy": asset.source_audio_policy,
        "timing_alignment_strategy": asset.timing_alignment_strategy,
        "metadata_payload": asset.metadata_payload,
        "download_url": download_url,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


def export_to_dict(export: ExportRecord, *, download_url: str | None = None) -> dict[str, object]:
    return {
        "id": export.id,
        "workspace_id": export.workspace_id,
        "project_id": export.project_id,
        "render_job_id": export.render_job_id,
        "asset_id": export.asset_id,
        "status": export.status,
        "file_name": export.file_name,
        "format": export.format,
        "bucket_name": export.bucket_name,
        "object_name": export.object_name,
        "duration_ms": export.duration_ms,
        "metadata_payload": export.metadata_payload,
        "download_url": download_url,
        "completed_at": export.completed_at,
        "created_at": export.created_at,
        "updated_at": export.updated_at,
    }
