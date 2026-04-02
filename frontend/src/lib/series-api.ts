import { api } from "./api-client";
import type {
  ScriptLine,
  SeriesCatalog,
  SeriesCatalogOption,
  SeriesDetail,
  SeriesInput,
  SeriesRun,
  SeriesRunStep,
  SeriesScript,
  SeriesSummary,
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
  language_key: string;
  voice_key: string;
  music_mode: "none" | "preset";
  music_keys: string[];
  art_style_key: string;
  caption_style_key: string;
  effect_keys: string[];
  total_script_count: number;
  latest_run_id: string | null;
  latest_run_status: string | null;
  active_run_id: string | null;
  active_run_status: string | null;
  can_edit?: boolean | null;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
};

type BackendSeriesDetail = BackendSeriesSummary & {
  custom_topic: string;
  custom_example_script: string;
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
  lines: Array<{
    id: string;
    scene_id: string;
    beat: string;
    narration: string;
    caption: string;
    duration_sec: number;
    status: string;
    visual_direction: string;
    voice_pacing: string;
  }>;
  created_at: string;
  updated_at: string;
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

function mapCatalogOption(option: BackendSeriesCatalogOption): SeriesCatalogOption {
  return {
    key: option.key,
    label: option.label,
    description: option.description,
    gender: option.gender ?? null,
    badge: option.badge ?? null,
  };
}

function mapScriptLine(line: BackendSeriesScript["lines"][number]): ScriptLine {
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

function mapSeriesSummary(series: BackendSeriesSummary): SeriesSummary {
  return {
    id: series.id,
    workspaceId: series.workspace_id,
    ownerUserId: series.owner_user_id,
    title: series.title,
    description: series.description,
    contentMode: series.content_mode,
    presetKey: series.preset_key,
    customTopic: "",
    customExampleScript: "",
    languageKey: series.language_key,
    voiceKey: series.voice_key,
    musicMode: series.music_mode,
    musicKeys: series.music_keys,
    artStyleKey: series.art_style_key,
    captionStyleKey: series.caption_style_key,
    effectKeys: series.effect_keys,
    totalScriptCount: series.total_script_count,
    latestRunId: series.latest_run_id,
    latestRunStatus: (series.latest_run_status as SeriesSummary["latestRunStatus"]) ?? null,
    activeRunId: series.active_run_id,
    activeRunStatus: (series.active_run_status as SeriesSummary["activeRunStatus"]) ?? null,
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
    createdAt: script.created_at,
    updatedAt: script.updated_at,
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

function buildSeriesPayload(input: SeriesInput) {
  return {
    title: input.title,
    description: input.description,
    content_mode: input.contentMode,
    preset_key: input.presetKey,
    custom_topic: input.customTopic,
    custom_example_script: input.customExampleScript,
    language_key: input.languageKey,
    voice_key: input.voiceKey,
    music_mode: input.musicMode,
    music_keys: input.musicKeys,
    art_style_key: input.artStyleKey,
    caption_style_key: input.captionStyleKey,
    effect_keys: input.effectKeys,
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
