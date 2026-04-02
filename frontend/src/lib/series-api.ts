import { api } from "./api-client";
import type {
  ScriptLine,
  SeriesCatalog,
  SeriesCatalogOption,
  SeriesDetail,
  SeriesInput,
  SeriesPublishedVideo,
  SeriesRevisionSummary,
  SeriesRun,
  SeriesRunStep,
  SeriesSceneAsset,
  SeriesScenePreview,
  SeriesScript,
  SeriesScriptDetail,
  SeriesSummary,
  SeriesVideoRun,
  SeriesVideoRunStep,
} from "../types/domain";

type BackendSeriesCatalogOption = {
  key: string;
  label: string;
  description: string;
  gender?: string | null;
  badge?: string | null;
};

type BackendSeriesCatalog = {
  content_presets: BackendSeriesCatalogOption[];
  languages: BackendSeriesCatalogOption[];
  voices: BackendSeriesCatalogOption[];
  music: BackendSeriesCatalogOption[];
  art_styles: BackendSeriesCatalogOption[];
  caption_styles: BackendSeriesCatalogOption[];
  effects: BackendSeriesCatalogOption[];
};

type BackendSeriesSummary = {
  id: string;
  workspace_id: string;
  owner_user_id: string;
  title: string;
  description: string;
  content_mode: "preset" | "custom";
  preset_key: string | null;
  custom_topic?: string;
  custom_example_script?: string;
  language_key: string;
  voice_key: string;
  music_mode: "none" | "preset";
  music_keys: string[];
  art_style_key: string;
  caption_style_key: string;
  effect_keys: string[];
  total_script_count: number;
  scripts_awaiting_review_count: number;
  approved_script_count: number;
  completed_video_count: number;
  latest_run_id: string | null;
  latest_run_status: string | null;
  active_run_id: string | null;
  active_run_status: string | null;
  active_video_run_id: string | null;
  active_video_run_status: string | null;
  primary_cta: "start_series" | "create_video";
  can_edit?: boolean | null;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
};

type BackendSeriesDetail = BackendSeriesSummary & {
  custom_topic: string;
  custom_example_script: string;
};

type BackendSeriesRevisionSummary = {
  id: string;
  series_script_id: string;
  revision_number: number;
  approval_state: "needs_review" | "approved" | "rejected" | "superseded";
  title: string;
  summary: string;
  estimated_duration_seconds: number;
  reading_time_label: string;
  total_words: number;
  lines: BackendScriptLine[];
  video_title: string;
  video_description: string;
  created_at: string;
  updated_at: string;
};

type BackendSeriesPublishedVideo = {
  project_id: string | null;
  render_job_id: string | null;
  export_id: string | null;
  download_url: string | null;
  title: string;
  description: string;
  completed_at: string | null;
};

type BackendScriptLine = {
  id: string;
  scene_id: string;
  beat: string;
  narration: string;
  caption: string;
  duration_sec: number;
  status: string;
  visual_direction: string;
  voice_pacing: string;
};

type BackendSeriesScript = {
  id: string;
  series_id: string;
  series_run_id: string;
  created_by_user_id: string | null;
  sequence_number: number;
  title: string;
  summary: string;
  estimated_duration_seconds: number;
  reading_time_label: string;
  total_words: number;
  lines: BackendScriptLine[];
  approval_state: "needs_review" | "approved" | "rejected" | "superseded";
  video_status: string | null;
  video_phase: string | null;
  video_current_scene_index: number | null;
  video_current_scene_count: number | null;
  video_render_job_id: string | null;
  video_hidden_project_id: string | null;
  current_revision: BackendSeriesRevisionSummary | null;
  approved_revision: BackendSeriesRevisionSummary | null;
  published_revision: BackendSeriesRevisionSummary | null;
  published_video: BackendSeriesPublishedVideo | null;
  can_approve: boolean;
  can_reject: boolean;
  can_regenerate: boolean;
  can_create_video: boolean;
  created_at: string;
  updated_at: string;
};

type BackendSeriesSceneAsset = {
  asset_id: string;
  download_url: string | null;
};

type BackendSeriesScenePreview = {
  scene_segment_id: string;
  scene_index: number;
  title: string;
  beat: string;
  narration_text: string;
  caption_text: string;
  target_duration_seconds: number;
  visual_prompt: string;
  start_image_prompt: string;
  end_image_prompt: string;
  start_frame_asset: BackendSeriesSceneAsset | null;
  end_frame_asset: BackendSeriesSceneAsset | null;
  narration_asset: BackendSeriesSceneAsset | null;
  slide_asset: BackendSeriesSceneAsset | null;
};

type BackendSeriesScriptDetail = {
  script: BackendSeriesScript;
  revisions: BackendSeriesRevisionSummary[];
  scenes: BackendSeriesScenePreview[];
  latest_render_job_id: string | null;
  latest_render_status: string | null;
  latest_scene_plan_id: string | null;
};

type BackendSeriesRunStep = {
  id: string;
  series_run_id: string;
  series_id: string;
  series_script_id: string | null;
  step_index: number;
  sequence_number: number;
  status: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

type BackendSeriesRun = {
  id: string;
  series_id: string;
  workspace_id: string;
  created_by_user_id: string;
  status: string;
  requested_script_count: number;
  completed_script_count: number;
  failed_script_count: number;
  idempotency_key: string;
  request_hash: string;
  payload: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  steps: BackendSeriesRunStep[];
  current_step: number | null;
};

type BackendSeriesVideoRunStep = {
  id: string;
  series_video_run_id: string;
  series_id: string;
  series_script_id: string;
  series_script_revision_id: string;
  step_index: number;
  sequence_number: number;
  status: string;
  phase:
    | "queued"
    | "preparing_project"
    | "generating_scenes"
    | "generating_frames"
    | "generating_voiceover"
    | "rendering"
    | "completed"
    | "failed";
  hidden_project_id: string | null;
  render_job_id: string | null;
  last_render_event_sequence: number;
  current_scene_index: number | null;
  current_scene_count: number | null;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

type BackendSeriesVideoRun = {
  id: string;
  series_id: string;
  workspace_id: string;
  created_by_user_id: string;
  status: string;
  requested_video_count: number;
  completed_video_count: number;
  failed_video_count: number;
  idempotency_key: string;
  request_hash: string;
  payload: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  steps: BackendSeriesVideoRunStep[];
  current_step: number | null;
};

function mapCatalogOption(option: BackendSeriesCatalogOption): SeriesCatalogOption {
  return {
    key: option.key,
    label: option.label,
    description: option.description,
    gender: option.gender ?? null,
    badge: option.badge ?? null,
  };
}

function mapScriptLine(line: BackendScriptLine): ScriptLine {
  return {
    id: line.id,
    sceneId: line.scene_id,
    beat: line.beat,
    narration: line.narration,
    caption: line.caption,
    durationSec: line.duration_sec,
    status: (line.status || "draft") as ScriptLine["status"],
    visualDirection: line.visual_direction,
    voicePacing: line.voice_pacing,
  };
}

function mapSeriesRevisionSummary(revision: BackendSeriesRevisionSummary): SeriesRevisionSummary {
  return {
    id: revision.id,
    seriesScriptId: revision.series_script_id,
    revisionNumber: revision.revision_number,
    approvalState: revision.approval_state,
    title: revision.title,
    summary: revision.summary,
    estimatedDurationSeconds: revision.estimated_duration_seconds,
    readingTimeLabel: revision.reading_time_label,
    totalWords: revision.total_words,
    lines: revision.lines.map(mapScriptLine),
    videoTitle: revision.video_title,
    videoDescription: revision.video_description,
    createdAt: revision.created_at,
    updatedAt: revision.updated_at,
  };
}

function mapSeriesPublishedVideo(video: BackendSeriesPublishedVideo): SeriesPublishedVideo {
  return {
    projectId: video.project_id,
    renderJobId: video.render_job_id,
    exportId: video.export_id,
    downloadUrl: video.download_url,
    title: video.title,
    description: video.description,
    completedAt: video.completed_at,
  };
}

function mapSeriesSummary(series: BackendSeriesSummary): SeriesSummary {
  return {
    id: series.id,
    workspaceId: series.workspace_id,
    ownerUserId: series.owner_user_id,
    title: series.title,
    description: series.description,
    contentMode: series.content_mode,
    presetKey: series.preset_key,
    customTopic: series.custom_topic ?? "",
    customExampleScript: series.custom_example_script ?? "",
    languageKey: series.language_key,
    voiceKey: series.voice_key,
    musicMode: series.music_mode,
    musicKeys: series.music_keys,
    artStyleKey: series.art_style_key,
    captionStyleKey: series.caption_style_key,
    effectKeys: series.effect_keys,
    totalScriptCount: series.total_script_count,
    scriptsAwaitingReviewCount: series.scripts_awaiting_review_count,
    approvedScriptCount: series.approved_script_count,
    completedVideoCount: series.completed_video_count,
    latestRunId: series.latest_run_id,
    latestRunStatus: (series.latest_run_status as SeriesSummary["latestRunStatus"]) ?? null,
    activeRunId: series.active_run_id,
    activeRunStatus: (series.active_run_status as SeriesSummary["activeRunStatus"]) ?? null,
    activeVideoRunId: series.active_video_run_id,
    activeVideoRunStatus: (series.active_video_run_status as SeriesSummary["activeVideoRunStatus"]) ?? null,
    primaryCta: series.primary_cta,
    canEdit: series.can_edit ?? true,
    lastActivityAt: series.last_activity_at,
    createdAt: series.created_at,
    updatedAt: series.updated_at,
  };
}

function mapSeriesDetail(series: BackendSeriesDetail): SeriesDetail {
  return {
    ...mapSeriesSummary(series),
    customTopic: series.custom_topic,
    customExampleScript: series.custom_example_script,
  };
}

function mapSeriesScript(script: BackendSeriesScript): SeriesScript {
  return {
    id: script.id,
    seriesId: script.series_id,
    seriesRunId: script.series_run_id,
    createdByUserId: script.created_by_user_id,
    sequenceNumber: script.sequence_number,
    title: script.title,
    summary: script.summary,
    estimatedDurationSeconds: script.estimated_duration_seconds,
    readingTimeLabel: script.reading_time_label,
    totalWords: script.total_words,
    lines: script.lines.map(mapScriptLine),
    approvalState: script.approval_state,
    videoStatus: (script.video_status as SeriesScript["videoStatus"]) ?? null,
    videoPhase: (script.video_phase as SeriesScript["videoPhase"]) ?? null,
    videoCurrentSceneIndex: script.video_current_scene_index,
    videoCurrentSceneCount: script.video_current_scene_count,
    videoRenderJobId: script.video_render_job_id,
    videoHiddenProjectId: script.video_hidden_project_id,
    currentRevision: script.current_revision ? mapSeriesRevisionSummary(script.current_revision) : null,
    approvedRevision: script.approved_revision ? mapSeriesRevisionSummary(script.approved_revision) : null,
    publishedRevision: script.published_revision ? mapSeriesRevisionSummary(script.published_revision) : null,
    publishedVideo: script.published_video ? mapSeriesPublishedVideo(script.published_video) : null,
    canApprove: script.can_approve,
    canReject: script.can_reject,
    canRegenerate: script.can_regenerate,
    canCreateVideo: script.can_create_video,
    createdAt: script.created_at,
    updatedAt: script.updated_at,
  };
}

function mapSeriesSceneAsset(asset: BackendSeriesSceneAsset | null): SeriesSceneAsset | null {
  if (!asset) {
    return null;
  }
  return {
    assetId: asset.asset_id,
    downloadUrl: asset.download_url,
  };
}

function mapSeriesScenePreview(scene: BackendSeriesScenePreview): SeriesScenePreview {
  return {
    sceneSegmentId: scene.scene_segment_id,
    sceneIndex: scene.scene_index,
    title: scene.title,
    beat: scene.beat,
    narrationText: scene.narration_text,
    captionText: scene.caption_text,
    targetDurationSeconds: scene.target_duration_seconds,
    visualPrompt: scene.visual_prompt,
    startImagePrompt: scene.start_image_prompt,
    endImagePrompt: scene.end_image_prompt,
    startFrameAsset: mapSeriesSceneAsset(scene.start_frame_asset),
    endFrameAsset: mapSeriesSceneAsset(scene.end_frame_asset),
    narrationAsset: mapSeriesSceneAsset(scene.narration_asset),
    slideAsset: mapSeriesSceneAsset(scene.slide_asset),
  };
}

function mapSeriesScriptDetail(detail: BackendSeriesScriptDetail): SeriesScriptDetail {
  return {
    script: mapSeriesScript(detail.script),
    revisions: detail.revisions.map(mapSeriesRevisionSummary),
    scenes: detail.scenes.map(mapSeriesScenePreview),
    latestRenderJobId: detail.latest_render_job_id,
    latestRenderStatus: (detail.latest_render_status as SeriesScriptDetail["latestRenderStatus"]) ?? null,
    latestScenePlanId: detail.latest_scene_plan_id,
  };
}

function mapSeriesRunStep(step: BackendSeriesRunStep): SeriesRunStep {
  return {
    id: step.id,
    seriesRunId: step.series_run_id,
    seriesId: step.series_id,
    seriesScriptId: step.series_script_id,
    stepIndex: step.step_index,
    sequenceNumber: step.sequence_number,
    status: step.status as SeriesRunStep["status"],
    inputPayload: step.input_payload,
    outputPayload: step.output_payload,
    errorCode: step.error_code,
    errorMessage: step.error_message,
    startedAt: step.started_at,
    completedAt: step.completed_at,
    createdAt: step.created_at,
    updatedAt: step.updated_at,
  };
}

function mapSeriesRun(run: BackendSeriesRun): SeriesRun {
  return {
    id: run.id,
    seriesId: run.series_id,
    workspaceId: run.workspace_id,
    createdByUserId: run.created_by_user_id,
    status: run.status as SeriesRun["status"],
    requestedScriptCount: run.requested_script_count,
    completedScriptCount: run.completed_script_count,
    failedScriptCount: run.failed_script_count,
    idempotencyKey: run.idempotency_key,
    requestHash: run.request_hash,
    payload: run.payload,
    errorCode: run.error_code,
    errorMessage: run.error_message,
    retryCount: run.retry_count,
    startedAt: run.started_at,
    completedAt: run.completed_at,
    cancelledAt: run.cancelled_at,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
    steps: run.steps.map(mapSeriesRunStep),
    currentStep: run.current_step,
  };
}

function mapSeriesVideoRunStep(step: BackendSeriesVideoRunStep): SeriesVideoRunStep {
  return {
    id: step.id,
    seriesVideoRunId: step.series_video_run_id,
    seriesId: step.series_id,
    seriesScriptId: step.series_script_id,
    seriesScriptRevisionId: step.series_script_revision_id,
    stepIndex: step.step_index,
    sequenceNumber: step.sequence_number,
    status: step.status as SeriesVideoRunStep["status"],
    phase: step.phase,
    hiddenProjectId: step.hidden_project_id,
    renderJobId: step.render_job_id,
    lastRenderEventSequence: step.last_render_event_sequence,
    currentSceneIndex: step.current_scene_index,
    currentSceneCount: step.current_scene_count,
    inputPayload: step.input_payload,
    outputPayload: step.output_payload,
    errorCode: step.error_code,
    errorMessage: step.error_message,
    startedAt: step.started_at,
    completedAt: step.completed_at,
    createdAt: step.created_at,
    updatedAt: step.updated_at,
  };
}

function mapSeriesVideoRun(run: BackendSeriesVideoRun): SeriesVideoRun {
  return {
    id: run.id,
    seriesId: run.series_id,
    workspaceId: run.workspace_id,
    createdByUserId: run.created_by_user_id,
    status: run.status as SeriesVideoRun["status"],
    requestedVideoCount: run.requested_video_count,
    completedVideoCount: run.completed_video_count,
    failedVideoCount: run.failed_video_count,
    idempotencyKey: run.idempotency_key,
    requestHash: run.request_hash,
    payload: run.payload,
    errorCode: run.error_code,
    errorMessage: run.error_message,
    retryCount: run.retry_count,
    startedAt: run.started_at,
    completedAt: run.completed_at,
    cancelledAt: run.cancelled_at,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
    steps: run.steps.map(mapSeriesVideoRunStep),
    currentStep: run.current_step,
  };
}

function buildSeriesPayload(input: SeriesInput) {
  const uniqueValues = (values: string[]) =>
    [...new Set(values.map((value) => value.trim()).filter(Boolean))];

  return {
    title: input.title.trim(),
    description: input.description.trim(),
    content_mode: input.contentMode,
    preset_key: input.contentMode === "preset" ? input.presetKey ?? null : null,
    custom_topic: input.contentMode === "custom" ? input.customTopic.trim() : "",
    custom_example_script: input.customExampleScript.trim(),
    language_key: input.languageKey.trim() || "en",
    voice_key: input.voiceKey.trim(),
    music_mode: input.musicMode,
    music_keys: input.musicMode === "preset" ? uniqueValues(input.musicKeys) : [],
    art_style_key: input.artStyleKey.trim(),
    caption_style_key: input.captionStyleKey.trim(),
    effect_keys: uniqueValues(input.effectKeys),
  };
}

function idempotencyHeaders(idempotencyKey?: string): Record<string, string> {
  return { "Idempotency-Key": idempotencyKey ?? crypto.randomUUID() };
}

export async function liveGetSeriesCatalog(): Promise<SeriesCatalog> {
  const catalog = await api.get<BackendSeriesCatalog>("/series/catalog");
  return {
    contentPresets: catalog.content_presets.map(mapCatalogOption),
    languages: catalog.languages.map(mapCatalogOption),
    voices: catalog.voices.map(mapCatalogOption),
    music: catalog.music.map(mapCatalogOption),
    artStyles: catalog.art_styles.map(mapCatalogOption),
    captionStyles: catalog.caption_styles.map(mapCatalogOption),
    effects: catalog.effects.map(mapCatalogOption),
  };
}

export async function liveGetSeriesList(): Promise<SeriesSummary[]> {
  const series = await api.get<BackendSeriesSummary[]>("/series");
  return series.map(mapSeriesSummary);
}

export async function liveGetSeriesDetail(seriesId: string): Promise<SeriesDetail> {
  const series = await api.get<BackendSeriesDetail>(`/series/${seriesId}`);
  return mapSeriesDetail(series);
}

export async function liveCreateSeries(input: SeriesInput): Promise<SeriesDetail> {
  const created = await api.post<BackendSeriesDetail>("/series", buildSeriesPayload(input));
  return mapSeriesDetail(created);
}

export async function liveUpdateSeries(seriesId: string, input: SeriesInput): Promise<SeriesDetail> {
  const updated = await api.patch<BackendSeriesDetail>(`/series/${seriesId}`, buildSeriesPayload(input));
  return mapSeriesDetail(updated);
}

export async function liveGetSeriesScripts(seriesId: string): Promise<SeriesScript[]> {
  const scripts = await api.get<BackendSeriesScript[]>(`/series/${seriesId}/scripts`);
  return scripts.map(mapSeriesScript);
}

export async function liveGetSeriesScriptDetail(seriesId: string, scriptId: string): Promise<SeriesScriptDetail> {
  const detail = await api.get<BackendSeriesScriptDetail>(`/series/${seriesId}/scripts/${scriptId}`);
  return mapSeriesScriptDetail(detail);
}

export async function liveApproveSeriesScript(seriesId: string, scriptId: string): Promise<SeriesScript> {
  const script = await api.post<BackendSeriesScript>(`/series/${seriesId}/scripts/${scriptId}:approve`, {});
  return mapSeriesScript(script);
}

export async function liveRejectSeriesScript(seriesId: string, scriptId: string): Promise<SeriesScript> {
  const script = await api.post<BackendSeriesScript>(`/series/${seriesId}/scripts/${scriptId}:reject`, {});
  return mapSeriesScript(script);
}

export async function liveRegenerateSeriesScript(
  seriesId: string,
  scriptId: string,
  idempotencyKey?: string,
): Promise<SeriesRun> {
  const run = await api.post<BackendSeriesRun>(
    `/series/${seriesId}/scripts/${scriptId}:regenerate`,
    {},
    idempotencyHeaders(idempotencyKey),
  );
  return mapSeriesRun(run);
}

export async function liveStartSeriesRun(
  seriesId: string,
  requestedScriptCount: number,
  idempotencyKey?: string,
): Promise<SeriesRun> {
  const run = await api.post<BackendSeriesRun>(
    `/series/${seriesId}/runs`,
    { requested_script_count: requestedScriptCount },
    idempotencyHeaders(idempotencyKey),
  );
  return mapSeriesRun(run);
}

export async function liveGetSeriesRun(seriesId: string, runId: string): Promise<SeriesRun> {
  const run = await api.get<BackendSeriesRun>(`/series/${seriesId}/runs/${runId}`);
  return mapSeriesRun(run);
}

export async function liveStartSeriesVideoRun(
  seriesId: string,
  seriesScriptIds: string[],
  idempotencyKey?: string,
): Promise<SeriesVideoRun> {
  const run = await api.post<BackendSeriesVideoRun>(
    `/series/${seriesId}/video-runs`,
    { series_script_ids: seriesScriptIds },
    idempotencyHeaders(idempotencyKey),
  );
  return mapSeriesVideoRun(run);
}

export async function liveGetSeriesVideoRun(seriesId: string, runId: string): Promise<SeriesVideoRun> {
  const run = await api.get<BackendSeriesVideoRun>(`/series/${seriesId}/video-runs/${runId}`);
  return mapSeriesVideoRun(run);
}
