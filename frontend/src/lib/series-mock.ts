import { ApiError } from "./api-client";
import type {
  ScriptLine,
  SeriesCatalog,
  SeriesDetail,
  SeriesInput,
  SeriesPublishedVideo,
  SeriesRevisionSummary,
  SeriesRun,
  SeriesScript,
  SeriesScriptDetail,
  SeriesScenePreview,
  SeriesSummary,
  SeriesVideoRun,
} from "../types/domain";

let mockCounter = 4000;

function nextId(prefix: string): string {
  mockCounter += 1;
  return `${prefix}_${mockCounter}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const SERIES_CATALOG: SeriesCatalog = {
  contentPresets: [
    { key: "scary_stories", label: "Scary stories", description: "Scary stories that give you goosebumps" },
    { key: "historical_figures", label: "Historical Figures", description: "Life story in one minute videos about the most important historical figures." },
    { key: "greek_mythology", label: "Greek Mythology", description: "Shocking and dramatic stories from Greek mythology." },
    { key: "important_events", label: "Important Events", description: "Viral videos about history spanning from ancient times to the modern day." },
    { key: "true_crime", label: "True Crime", description: "Viral videos about true crime stories." },
    { key: "stoic_motivation", label: "Stoic Motivation", description: "Viral videos about stoic philosophy and life lessons." },
    { key: "good_morals", label: "Good morals", description: "Viral videos that teach people good morals and life lessons." },
  ],
  languages: [{ key: "en", label: "English", description: "UK English short-form narration." }],
  voices: [
    { key: "adam", label: "Adam", description: "The well known voice of tiktok and instagram.", gender: "Male" },
    { key: "john", label: "John", description: "The perfect storyteller, very realistic and natural.", gender: "Male" },
    { key: "confident_narrator", label: "Confident Narrator", description: "Polished and direct for educational and news content.", gender: "Male" },
    { key: "warm_storyteller", label: "Warm Storyteller", description: "Friendly, human, and good for emotional arcs.", gender: "Female" },
    { key: "ava_editorial", label: "Ava Editorial", description: "Premium editorial pacing with a composed delivery.", gender: "Female" },
    { key: "energetic_host", label: "Energetic Host", description: "Fast and punchy for viral short-form pacing.", gender: "Female" },
  ],
  music: [
    { key: "happy_rhythm", label: "Happy rhythm", description: "Upbeat and energetic, perfect for positive content" },
    { key: "quiet_before_storm", label: "Quiet before storm", description: "Building tension and anticipation for dramatic reveals" },
    { key: "brilliant_symphony", label: "Brilliant symphony", description: "Orchestral and majestic for epic storytelling" },
    { key: "breathing_shadows", label: "Breathing shadows", description: "Mysterious and eerie ambiance for suspenseful videos" },
    { key: "eight_bit_slowed", label: "8-bit slowed", description: "Eerie chiptune with a haunting retro feel" },
    { key: "deep_bass", label: "Deep bass", description: "Dark interstellar atmosphere with deep low-end" },
  ],
  artStyles: [
    { key: "comic", label: "Comic", description: "Graphic panels with stylized shading." },
    { key: "creepy_comic", label: "Creepy Comic", description: "Dark comic frames with horror textures." },
    { key: "modern_cartoon", label: "Modern Cartoon", description: "Clean and expressive cartoon animation." },
    { key: "disney", label: "Disney", description: "Whimsical cinematic character-driven frames." },
    { key: "mythology", label: "Mythology", description: "Ancient-epic scenes with dramatic scale." },
    { key: "pixel_art", label: "Pixel Art", description: "Retro pixel scenes and bold silhouettes." },
    { key: "ghibli", label: "Ghibli", description: "Painterly, atmospheric, and warm storytelling." },
    { key: "anime", label: "Anime", description: "High-energy anime-inspired action and emotion." },
    { key: "painting", label: "Painting", description: "Brush-textured painterly compositions." },
    { key: "dark_fantasy", label: "Dark Fantasy", description: "Moody, gothic, and fantastical worlds." },
    { key: "lego", label: "Lego", description: "Brick-built miniature scenes with playful charm." },
    { key: "polaroid", label: "Polaroid", description: "Vintage instant-photo frames and textures." },
    { key: "realism", label: "Realism", description: "Photorealistic compositions and grounded detail." },
    { key: "fantastic", label: "Fantastic", description: "Surreal, imaginative, and cinematic visuals." },
  ],
  captionStyles: [
    { key: "bold_stroke", label: "Bold Stroke", description: "Heavy all-caps captions with a strong outline." },
    { key: "red_highlight", label: "Red Highlight", description: "Impact captions with red emphasis words." },
    { key: "sleek", label: "Sleek", description: "Minimal modern caption styling." },
    { key: "karaoke", label: "Karaoke", description: "Word-by-word highlight timing." },
    { key: "majestic", label: "Majestic", description: "Cinematic serif styling for epic narration." },
    { key: "beast", label: "Beast", description: "Aggressive bold captions for hype content." },
    { key: "elegant", label: "Elegant", description: "Refined high-contrast typography." },
    { key: "pixel", label: "Pixel", description: "Retro pixel caption styling." },
    { key: "clarity", label: "Clarity", description: "High legibility with calm contrast." },
  ],
  effects: [
    { key: "shake_effect", label: "Shake effect", description: "Subjects pop out with eerie motion for suspenseful stories.", badge: "New" },
    { key: "film_grain", label: "Film grain", description: "Add an old film look with scanlines and dust.", badge: "New" },
    { key: "animated_hook", label: "Animated hook", description: "Generate a 5-second hook scene.", badge: "Premium" },
  ],
};

type Slot = {
  id: string;
  seriesId: string;
  seriesRunId: string;
  sequenceNumber: number;
  revisions: SeriesRevisionSummary[];
  currentRevisionId: string;
  approvedRevisionId: string | null;
  publishedRevisionId: string | null;
  publishedVideo: SeriesPublishedVideo | null;
  scenes: SeriesScenePreview[];
  createdAt: string;
  updatedAt: string;
};

const seriesStore: SeriesDetail[] = [];
const slotStore = new Map<string, Slot[]>();
const runStore = new Map<string, SeriesRun[]>();
const videoRunStore = new Map<string, SeriesVideoRun[]>();

function buildLines(series: SeriesDetail, sequenceNumber: number): ScriptLine[] {
  return [
    {
      id: `${sequenceNumber}-1`,
      sceneId: `${sequenceNumber}-scene-1`,
      beat: "Hook",
      narration: `${series.title} episode ${sequenceNumber} opens with a strong scroll-stopping hook.`,
      caption: "Hook",
      durationSec: 10,
      status: "draft",
      visualDirection: `${series.artStyleKey} dramatic opener`,
      voicePacing: series.voiceKey,
    },
    {
      id: `${sequenceNumber}-2`,
      sceneId: `${sequenceNumber}-scene-2`,
      beat: "Payoff",
      narration: "The middle delivers context fast and lands with a memorable payoff.",
      caption: "Payoff",
      durationSec: 14,
      status: "draft",
      visualDirection: `${series.artStyleKey} cinematic payoff`,
      voicePacing: series.voiceKey,
    },
  ];
}

function createRevision(series: SeriesDetail, slotId: string, sequenceNumber: number, revisionNumber: number): SeriesRevisionSummary {
  const lines = buildLines(series, sequenceNumber);
  return {
    id: nextId("series_revision"),
    seriesScriptId: slotId,
    revisionNumber,
    approvalState: "needs_review",
    title: `${series.title} Episode ${sequenceNumber}${revisionNumber > 1 ? ` Rev ${revisionNumber}` : ""}`,
    summary: `A one-minute ${series.title.toLowerCase()} episode designed for strong short-form retention.`,
    estimatedDurationSeconds: 24,
    readingTimeLabel: "24s narration",
    totalWords: lines.reduce((sum, line) => sum + line.narration.split(/\s+/).filter(Boolean).length, 0),
    lines,
    videoTitle: "",
    videoDescription: "",
    createdAt: nowIso(),
    updatedAt: nowIso(),
  };
}

function getSeries(seriesId: string): SeriesDetail {
  const series = seriesStore.find((item) => item.id === seriesId);
  if (!series) {
    throw new ApiError(404, "series_not_found", "Series not found.");
  }
  return series;
}

function getSlots(seriesId: string): Slot[] {
  return slotStore.get(seriesId) ?? [];
}

function currentRevision(slot: Slot) {
  return slot.revisions.find((item) => item.id === slot.currentRevisionId) ?? slot.revisions[slot.revisions.length - 1];
}

function approvedRevision(slot: Slot) {
  return slot.revisions.find((item) => item.id === slot.approvedRevisionId) ?? null;
}

function publishedRevision(slot: Slot) {
  return slot.revisions.find((item) => item.id === slot.publishedRevisionId) ?? null;
}

function toScript(slot: Slot): SeriesScript {
  const current = currentRevision(slot);
  const approved = approvedRevision(slot);
  const published = publishedRevision(slot);
  return {
    id: slot.id,
    seriesId: slot.seriesId,
    seriesRunId: slot.seriesRunId,
    createdByUserId: "user_1",
    sequenceNumber: slot.sequenceNumber,
    title: current.title,
    summary: current.summary,
    estimatedDurationSeconds: current.estimatedDurationSeconds,
    readingTimeLabel: current.readingTimeLabel,
    totalWords: current.totalWords,
    lines: current.lines,
    approvalState: current.approvalState,
    videoStatus: slot.publishedVideo ? "completed" : null,
    videoPhase: slot.publishedVideo ? "completed" : null,
    videoCurrentSceneIndex: null,
    videoCurrentSceneCount: slot.scenes.length || null,
    videoRenderJobId: slot.publishedVideo?.renderJobId ?? null,
    videoHiddenProjectId: slot.publishedVideo?.projectId ?? null,
    currentRevision: current,
    approvedRevision: approved,
    publishedRevision: published,
    publishedVideo: slot.publishedVideo,
    canApprove: current.approvalState !== "approved",
    canReject: current.approvalState !== "rejected",
    canRegenerate: true,
    canCreateVideo: Boolean(slot.approvedRevisionId && slot.approvedRevisionId !== slot.publishedRevisionId),
    createdAt: slot.createdAt,
    updatedAt: slot.updatedAt,
  };
}

function updateSeriesCounts(seriesId: string) {
  const series = getSeries(seriesId);
  const slots = getSlots(seriesId);
  series.totalScriptCount = slots.length;
  series.scriptsAwaitingReviewCount = slots.filter((slot) => currentRevision(slot).approvalState === "needs_review").length;
  series.approvedScriptCount = slots.filter((slot) => Boolean(slot.approvedRevisionId)).length;
  series.completedVideoCount = slots.filter((slot) => Boolean(slot.publishedVideo)).length;
  series.primaryCta = slots.length > 0 ? "create_video" : "start_series";
  series.lastActivityAt = nowIso();
  series.updatedAt = nowIso();
  series.latestRunId = runStore.get(seriesId)?.[0]?.id ?? null;
  series.latestRunStatus = runStore.get(seriesId)?.[0]?.status ?? null;
  series.activeRunId = null;
  series.activeRunStatus = null;
  series.activeVideoRunId = null;
  series.activeVideoRunStatus = null;
}

function createSeriesRun(seriesId: string, count: number, idempotencyKey: string): SeriesRun {
  const series = getSeries(seriesId);
  const createdAt = nowIso();
  const startingCount = getSlots(seriesId).length;
  const run: SeriesRun = {
    id: nextId("series_run"),
    seriesId,
    workspaceId: series.workspaceId,
    createdByUserId: series.ownerUserId,
    status: "completed",
    requestedScriptCount: count,
    completedScriptCount: count,
    failedScriptCount: 0,
    idempotencyKey,
    requestHash: idempotencyKey,
    payload: {},
    errorCode: null,
    errorMessage: null,
    retryCount: 0,
    startedAt: createdAt,
    completedAt: createdAt,
    cancelledAt: null,
    createdAt,
    updatedAt: createdAt,
    steps: [],
    currentStep: null,
  };
  const slots = getSlots(seriesId);
  for (let index = 0; index < count; index += 1) {
    const sequenceNumber = startingCount + index + 1;
    const slotId = nextId("series_script");
    const revision = createRevision(series, slotId, sequenceNumber, 1);
    slots.push({
      id: slotId,
      seriesId,
      seriesRunId: run.id,
      sequenceNumber,
      revisions: [revision],
      currentRevisionId: revision.id,
      approvedRevisionId: null,
      publishedRevisionId: null,
      publishedVideo: null,
      scenes: [],
      createdAt,
      updatedAt: createdAt,
    });
    run.steps.push({
      id: nextId("series_step"),
      seriesRunId: run.id,
      seriesId,
      seriesScriptId: slotId,
      stepIndex: index + 1,
      sequenceNumber,
      status: "completed",
      inputPayload: { sequenceNumber },
      outputPayload: { seriesScriptId: slotId },
      errorCode: null,
      errorMessage: null,
      startedAt: createdAt,
      completedAt: createdAt,
      createdAt,
      updatedAt: createdAt,
    });
  }
  slotStore.set(seriesId, slots.sort((a, b) => a.sequenceNumber - b.sequenceNumber));
  runStore.set(seriesId, [run, ...(runStore.get(seriesId) ?? [])]);
  updateSeriesCounts(seriesId);
  return run;
}

function createVideoRun(seriesId: string, seriesScriptIds: string[], idempotencyKey: string): SeriesVideoRun {
  const series = getSeries(seriesId);
  const createdAt = nowIso();
  const eligible = getSlots(seriesId).filter((slot) => {
    const selected = seriesScriptIds.length === 0 || seriesScriptIds.includes(slot.id);
    return selected && Boolean(slot.approvedRevisionId) && slot.approvedRevisionId !== slot.publishedRevisionId;
  });
  if (eligible.length === 0) {
    throw new ApiError(400, "no_series_videos_eligible", "No approved scripts are eligible for video creation.");
  }
  const run: SeriesVideoRun = {
    id: nextId("series_video_run"),
    seriesId,
    workspaceId: series.workspaceId,
    createdByUserId: series.ownerUserId,
    status: "completed",
    requestedVideoCount: eligible.length,
    completedVideoCount: eligible.length,
    failedVideoCount: 0,
    idempotencyKey,
    requestHash: idempotencyKey,
    payload: { seriesScriptIds },
    errorCode: null,
    errorMessage: null,
    retryCount: 0,
    startedAt: createdAt,
    completedAt: createdAt,
    cancelledAt: null,
    createdAt,
    updatedAt: createdAt,
    steps: eligible.map((slot, index) => ({
      id: nextId("series_video_step"),
      seriesVideoRunId: "",
      seriesId,
      seriesScriptId: slot.id,
      seriesScriptRevisionId: slot.approvedRevisionId ?? slot.currentRevisionId,
      stepIndex: index + 1,
      sequenceNumber: slot.sequenceNumber,
      status: "completed",
      phase: "completed",
      hiddenProjectId: nextId("project_internal"),
      renderJobId: nextId("render"),
      lastRenderEventSequence: 6,
      currentSceneIndex: 2,
      currentSceneCount: 2,
      inputPayload: {},
      outputPayload: {},
      errorCode: null,
      errorMessage: null,
      startedAt: createdAt,
      completedAt: createdAt,
      createdAt,
      updatedAt: createdAt,
    })),
    currentStep: null,
  };
  run.steps.forEach((step) => {
    step.seriesVideoRunId = run.id;
    const slot = eligible.find((item) => item.id === step.seriesScriptId);
    if (!slot) {
      return;
    }
    const approved = approvedRevision(slot);
    if (!approved) {
      return;
    }
    approved.videoTitle = `${approved.title} | Viral Short`;
    approved.videoDescription = `${approved.summary}\n#Series #Shorts #Viral`;
    slot.publishedRevisionId = approved.id;
    slot.publishedVideo = {
      projectId: step.hiddenProjectId,
      renderJobId: step.renderJobId,
      exportId: nextId("export"),
      downloadUrl: `/mock/video/${slot.id}.mp4`,
      title: approved.videoTitle,
      description: approved.videoDescription,
      completedAt: createdAt,
    };
    slot.scenes = approved.lines.map((line, index) => ({
      sceneSegmentId: nextId("scene_segment"),
      sceneIndex: index + 1,
      title: `${approved.title} Scene ${index + 1}`,
      beat: line.beat,
      narrationText: line.narration,
      captionText: line.caption,
      targetDurationSeconds: line.durationSec,
      visualPrompt: `${series.artStyleKey} ${line.beat}`,
      startImagePrompt: `Start ${line.beat}`,
      endImagePrompt: `End ${line.beat}`,
      startFrameAsset: { assetId: nextId("asset"), downloadUrl: null },
      endFrameAsset: { assetId: nextId("asset"), downloadUrl: null },
      narrationAsset: { assetId: nextId("asset"), downloadUrl: "/mock/audio/narration.mp3" },
      slideAsset: { assetId: nextId("asset"), downloadUrl: "/mock/video/scene.mp4" },
    }));
  });
  videoRunStore.set(seriesId, [run, ...(videoRunStore.get(seriesId) ?? [])]);
  updateSeriesCounts(seriesId);
  return run;
}

export async function mockGetSeriesCatalog(): Promise<SeriesCatalog> {
  return clone(SERIES_CATALOG);
}

export async function mockGetSeriesList(): Promise<SeriesSummary[]> {
  seriesStore.forEach((series) => updateSeriesCounts(series.id));
  return clone(seriesStore);
}

export async function mockGetSeriesDetail(seriesId: string): Promise<SeriesDetail> {
  updateSeriesCounts(seriesId);
  return clone(getSeries(seriesId));
}

export async function mockCreateSeries(input: SeriesInput): Promise<SeriesDetail> {
  const createdAt = nowIso();
  const series: SeriesDetail = {
    id: nextId("series"),
    workspaceId: "workspace_north_star",
    ownerUserId: "user_1",
    title: input.title,
    description: input.description,
    contentMode: input.contentMode,
    presetKey: input.presetKey,
    customTopic: input.customTopic,
    customExampleScript: input.customExampleScript,
    languageKey: input.languageKey,
    voiceKey: input.voiceKey,
    musicMode: input.musicMode,
    musicKeys: [...input.musicKeys],
    artStyleKey: input.artStyleKey,
    captionStyleKey: input.captionStyleKey,
    effectKeys: [...input.effectKeys],
    totalScriptCount: 0,
    scriptsAwaitingReviewCount: 0,
    approvedScriptCount: 0,
    completedVideoCount: 0,
    latestRunId: null,
    latestRunStatus: null,
    activeRunId: null,
    activeRunStatus: null,
    activeVideoRunId: null,
    activeVideoRunStatus: null,
    primaryCta: "start_series",
    canEdit: true,
    lastActivityAt: createdAt,
    createdAt,
    updatedAt: createdAt,
  };
  seriesStore.unshift(series);
  slotStore.set(series.id, []);
  runStore.set(series.id, []);
  videoRunStore.set(series.id, []);
  return clone(series);
}

export async function mockUpdateSeries(seriesId: string, input: SeriesInput): Promise<SeriesDetail> {
  const series = getSeries(seriesId);
  Object.assign(series, {
    title: input.title,
    description: input.description,
    contentMode: input.contentMode,
    presetKey: input.presetKey,
    customTopic: input.customTopic,
    customExampleScript: input.customExampleScript,
    languageKey: input.languageKey,
    voiceKey: input.voiceKey,
    musicMode: input.musicMode,
    musicKeys: [...input.musicKeys],
    artStyleKey: input.artStyleKey,
    captionStyleKey: input.captionStyleKey,
    effectKeys: [...input.effectKeys],
    updatedAt: nowIso(),
  });
  updateSeriesCounts(seriesId);
  return clone(series);
}

export async function mockGetSeriesScripts(seriesId: string): Promise<SeriesScript[]> {
  updateSeriesCounts(seriesId);
  return clone(getSlots(seriesId).map(toScript));
}

export async function mockGetSeriesScriptDetail(seriesId: string, scriptId: string): Promise<SeriesScriptDetail> {
  const slot = getSlots(seriesId).find((item) => item.id === scriptId);
  if (!slot) {
    throw new ApiError(404, "series_script_not_found", "Series script not found.");
  }
  return clone({
    script: toScript(slot),
    revisions: slot.revisions.slice().sort((a, b) => b.revisionNumber - a.revisionNumber),
    scenes: slot.scenes,
    latestRenderJobId: slot.publishedVideo?.renderJobId ?? null,
    latestRenderStatus: slot.publishedVideo ? "completed" : null,
    latestScenePlanId: slot.scenes[0]?.sceneSegmentId ?? null,
  });
}

export async function mockApproveSeriesScript(seriesId: string, scriptId: string): Promise<SeriesScript> {
  const slot = getSlots(seriesId).find((item) => item.id === scriptId);
  if (!slot) {
    throw new ApiError(404, "series_script_not_found", "Series script not found.");
  }
  const revision = currentRevision(slot);
  revision.approvalState = "approved";
  slot.approvedRevisionId = revision.id;
  slot.updatedAt = nowIso();
  updateSeriesCounts(seriesId);
  return clone(toScript(slot));
}

export async function mockRejectSeriesScript(seriesId: string, scriptId: string): Promise<SeriesScript> {
  const slot = getSlots(seriesId).find((item) => item.id === scriptId);
  if (!slot) {
    throw new ApiError(404, "series_script_not_found", "Series script not found.");
  }
  const revision = currentRevision(slot);
  revision.approvalState = "rejected";
  if (slot.approvedRevisionId === revision.id) {
    slot.approvedRevisionId = null;
  }
  slot.updatedAt = nowIso();
  updateSeriesCounts(seriesId);
  return clone(toScript(slot));
}

export async function mockRegenerateSeriesScript(seriesId: string, scriptId: string, idempotencyKey: string): Promise<SeriesRun> {
  const existing = runStore.get(seriesId)?.find((item) => item.idempotencyKey === idempotencyKey);
  if (existing) {
    return clone(existing);
  }
  const slot = getSlots(seriesId).find((item) => item.id === scriptId);
  if (!slot) {
    throw new ApiError(404, "series_script_not_found", "Series script not found.");
  }
  const series = getSeries(seriesId);
  const revision = createRevision(series, slot.id, slot.sequenceNumber, slot.revisions.length + 1);
  slot.revisions.push(revision);
  slot.currentRevisionId = revision.id;
  slot.updatedAt = nowIso();
  const run = createSeriesRun(seriesId, 0, idempotencyKey);
  run.requestedScriptCount = 1;
  run.completedScriptCount = 1;
  run.steps = [
    {
      id: nextId("series_step"),
      seriesRunId: run.id,
      seriesId,
      seriesScriptId: scriptId,
      stepIndex: 1,
      sequenceNumber: slot.sequenceNumber,
      status: "completed",
      inputPayload: { mode: "regenerate" },
      outputPayload: { seriesScriptId: scriptId },
      errorCode: null,
      errorMessage: null,
      startedAt: run.createdAt,
      completedAt: run.createdAt,
      createdAt: run.createdAt,
      updatedAt: run.createdAt,
    },
  ];
  updateSeriesCounts(seriesId);
  return clone(run);
}

export async function mockStartSeriesRun(seriesId: string, requestedScriptCount: number, idempotencyKey: string): Promise<SeriesRun> {
  const existing = runStore.get(seriesId)?.find((item) => item.idempotencyKey === idempotencyKey);
  if (existing) {
    return clone(existing);
  }
  return clone(createSeriesRun(seriesId, requestedScriptCount, idempotencyKey));
}

export async function mockGetSeriesRun(seriesId: string, runId: string): Promise<SeriesRun> {
  const run = runStore.get(seriesId)?.find((item) => item.id === runId);
  if (!run) {
    throw new ApiError(404, "series_run_not_found", "Series run not found.");
  }
  return clone(run);
}

export async function mockStartSeriesVideoRun(seriesId: string, seriesScriptIds: string[], idempotencyKey: string): Promise<SeriesVideoRun> {
  const existing = videoRunStore.get(seriesId)?.find((item) => item.idempotencyKey === idempotencyKey);
  if (existing) {
    return clone(existing);
  }
  return clone(createVideoRun(seriesId, seriesScriptIds, idempotencyKey));
}

export async function mockGetSeriesVideoRun(seriesId: string, runId: string): Promise<SeriesVideoRun> {
  const run = videoRunStore.get(seriesId)?.find((item) => item.id === runId);
  if (!run) {
    throw new ApiError(404, "series_video_run_not_found", "Series video run not found.");
  }
  return clone(run);
}
