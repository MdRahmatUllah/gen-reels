import { ApiError } from "./api-client";
import type {
  ScriptLine,
  SeriesCatalog,
  SeriesDetail,
  SeriesInput,
  SeriesRun,
  SeriesScript,
  SeriesSummary,
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
    { key: "shake_effect", label: "Shake effect", description: "Subjects pop out with eerie motion — great for horror, thriller, and suspenseful stories.", badge: "New" },
    { key: "film_grain", label: "Film grain", description: "Add an old film look with scanlines, dust particles, noise, and a subtle vignette.", badge: "New" },
    { key: "animated_hook", label: "Animated hook", description: "Generate a 5-second motion video for the first scene to hook viewers instantly.", badge: "Premium" },
  ],
};

type InternalState = {
  series: SeriesDetail[];
  scriptsBySeriesId: Map<string, SeriesScript[]>;
  runsBySeriesId: Map<string, SeriesRun[]>;
  timeoutsByRunId: Map<string, ReturnType<typeof setTimeout>>;
};

const seedSeriesId = "series_seed_history";
const seedRunId = "series_run_seed_history";
const seedNow = nowIso();

const state: InternalState = {
  series: [
    {
      id: seedSeriesId,
      workspaceId: "workspace_north_star",
      ownerUserId: "user_1",
      title: "History In One Breath",
      description: "Fast-moving history stories built for short-form reels.",
      contentMode: "preset",
      presetKey: "important_events",
      customTopic: "",
      customExampleScript: "",
      languageKey: "en",
      voiceKey: "john",
      musicMode: "preset",
      musicKeys: ["brilliant_symphony"],
      artStyleKey: "realism",
      captionStyleKey: "clarity",
      effectKeys: [],
      totalScriptCount: 1,
      latestRunId: seedRunId,
      latestRunStatus: "completed",
      activeRunId: null,
      activeRunStatus: null,
      canEdit: true,
      lastActivityAt: seedNow,
      createdAt: seedNow,
      updatedAt: seedNow,
    },
  ],
  scriptsBySeriesId: new Map([
    [
      seedSeriesId,
      [
        {
          id: "series_script_seed_1",
          seriesId: seedSeriesId,
          seriesRunId: seedRunId,
          createdByUserId: "user_1",
          sequenceNumber: 1,
          title: "How Pompeii Froze In Time",
          summary: "A quick dramatic retelling of the eruption of Mount Vesuvius and the city it preserved.",
          estimatedDurationSeconds: 62,
          readingTimeLabel: "62s narration",
          totalWords: 116,
          lines: [
            {
              id: "line_01",
              sceneId: "scene_01",
              beat: "Hook",
              narration: "Imagine waking up to ash falling from the sky before breakfast.",
              caption: "Pompeii had no warning",
              durationSec: 10,
              status: "draft",
              visualDirection: "A sunlit Roman street darkening under volcanic ash.",
              voicePacing: "Urgent",
            },
            {
              id: "line_02",
              sceneId: "scene_02",
              beat: "Setup",
              narration: "In 79 AD, Mount Vesuvius erupted and buried Pompeii in hours.",
              caption: "79 AD",
              durationSec: 12,
              status: "draft",
              visualDirection: "Wide view of the volcano looming behind the city.",
              voicePacing: "Measured",
            },
          ],
          createdAt: seedNow,
          updatedAt: seedNow,
        },
      ],
    ],
  ]),
  runsBySeriesId: new Map([
    [
      seedSeriesId,
      [
        {
          id: seedRunId,
          seriesId: seedSeriesId,
          workspaceId: "workspace_north_star",
          createdByUserId: "user_1",
          status: "completed",
          requestedScriptCount: 1,
          completedScriptCount: 1,
          failedScriptCount: 0,
          idempotencyKey: "seed-run",
          requestHash: "seed-run",
          payload: {},
          errorCode: null,
          errorMessage: null,
          retryCount: 0,
          startedAt: seedNow,
          completedAt: seedNow,
          cancelledAt: null,
          createdAt: seedNow,
          updatedAt: seedNow,
          steps: [
            {
              id: "series_step_seed_1",
              seriesRunId: seedRunId,
              seriesId: seedSeriesId,
              seriesScriptId: "series_script_seed_1",
              stepIndex: 1,
              sequenceNumber: 1,
              status: "completed",
              inputPayload: { sequenceNumber: 1 },
              outputPayload: { title: "How Pompeii Froze In Time" },
              errorCode: null,
              errorMessage: null,
              startedAt: seedNow,
              completedAt: seedNow,
              createdAt: seedNow,
              updatedAt: seedNow,
            },
          ],
          currentStep: null,
        },
      ],
    ],
  ]),
  timeoutsByRunId: new Map(),
};

function getSeries(seriesId: string): SeriesDetail {
  const series = state.series.find((item) => item.id === seriesId);
  if (!series) {
    throw new ApiError(404, "series_not_found", "Series not found.");
  }
  return series;
}

function getRuns(seriesId: string): SeriesRun[] {
  return state.runsBySeriesId.get(seriesId) ?? [];
}

function getScripts(seriesId: string): SeriesScript[] {
  return state.scriptsBySeriesId.get(seriesId) ?? [];
}

function activeRun(seriesId: string): SeriesRun | null {
  return getRuns(seriesId).find((run) => run.status === "queued" || run.status === "running") ?? null;
}

function latestRun(seriesId: string): SeriesRun | null {
  return getRuns(seriesId).slice().sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0] ?? null;
}

function summarize(series: SeriesDetail): SeriesSummary {
  const scripts = getScripts(series.id);
  const latest = latestRun(series.id);
  const active = activeRun(series.id);
  const lastActivityAt = [
    series.updatedAt,
    latest?.updatedAt ?? "",
    scripts[scripts.length - 1]?.createdAt ?? "",
  ]
    .filter(Boolean)
    .sort()
    .at(-1) ?? series.updatedAt;
  return {
    ...series,
    totalScriptCount: scripts.length,
    latestRunId: latest?.id ?? null,
    latestRunStatus: latest?.status ?? null,
    activeRunId: active?.id ?? null,
    activeRunStatus: active?.status ?? null,
    canEdit: active === null,
    lastActivityAt,
  };
}

function syncSeriesSummary(seriesId: string): void {
  const current = getSeries(seriesId);
  const summary = summarize(current);
  const index = state.series.findIndex((item) => item.id === seriesId);
  state.series[index] = summary;
}

function buildScriptLines(series: SeriesDetail, sequenceNumber: number): ScriptLine[] {
  const topic =
    SERIES_CATALOG.contentPresets.find((item) => item.key === series.presetKey)?.label ??
    series.customTopic ??
    series.title;
  const voice =
    SERIES_CATALOG.voices.find((item) => item.key === series.voiceKey)?.label ?? series.voiceKey;
  const art =
    SERIES_CATALOG.artStyles.find((item) => item.key === series.artStyleKey)?.label ?? series.artStyleKey;
  return [
    {
      id: `${sequenceNumber}_line_01`,
      sceneId: `${sequenceNumber}_scene_01`,
      beat: "Hook",
      narration: `Here is episode ${sequenceNumber} of ${series.title}: a fresh ${topic.toLowerCase()} angle designed to stop the scroll instantly.`,
      caption: `${series.title} episode ${sequenceNumber}`,
      durationSec: 10,
      status: "draft",
      visualDirection: `${art} hook frame with a bold opening caption.`,
      voicePacing: voice,
    },
    {
      id: `${sequenceNumber}_line_02`,
      sceneId: `${sequenceNumber}_scene_02`,
      beat: "Context",
      narration: `Set the scene fast, explain why this moment matters, and keep the tone tight and social-first.`,
      caption: "Why this matters",
      durationSec: 12,
      status: "draft",
      visualDirection: `${art} mid-shot that anchors the setting and the stakes.`,
      voicePacing: voice,
    },
    {
      id: `${sequenceNumber}_line_03`,
      sceneId: `${sequenceNumber}_scene_03`,
      beat: "Twist",
      narration: `Add the surprising turn that makes this episode feel different from the rest of the series.`,
      caption: "The twist",
      durationSec: 12,
      status: "draft",
      visualDirection: `${art} reveal frame with heightened drama and movement.`,
      voicePacing: voice,
    },
    {
      id: `${sequenceNumber}_line_04`,
      sceneId: `${sequenceNumber}_scene_04`,
      beat: "Payoff",
      narration: `Land the payoff clearly, then close with a memorable final line viewers will want to repeat.`,
      caption: "Final payoff",
      durationSec: 14,
      status: "draft",
      visualDirection: `${art} closing composition with the main subject centered and cinematic detail.`,
      voicePacing: voice,
    },
  ];
}

function buildGeneratedScript(series: SeriesDetail, sequenceNumber: number): SeriesScript {
  const topic =
    SERIES_CATALOG.contentPresets.find((item) => item.key === series.presetKey)?.label ??
    "Custom series";
  const lines = buildScriptLines(series, sequenceNumber);
  return {
    id: nextId("series_script"),
    seriesId: series.id,
    seriesRunId: "",
    createdByUserId: "user_1",
    sequenceNumber,
    title: `${series.title} Episode ${sequenceNumber}`,
    summary: `A ${topic.toLowerCase()} script generated for episode ${sequenceNumber}, designed for one-minute short-form storytelling.`,
    estimatedDurationSeconds: lines.reduce((sum, line) => sum + line.durationSec, 0),
    readingTimeLabel: "48s narration",
    totalWords: lines.reduce((sum, line) => sum + line.narration.split(/\s+/).filter(Boolean).length, 0),
    lines,
    createdAt: nowIso(),
    updatedAt: nowIso(),
  };
}

function queueNextStep(seriesId: string, runId: string, stepIndex: number): void {
  const timeoutId = setTimeout(() => {
    const run = getRuns(seriesId).find((item) => item.id === runId);
    if (!run || run.status === "failed" || run.status === "cancelled") {
      return;
    }
    const step = run.steps[stepIndex];
    if (!step) {
      run.status = "completed";
      run.currentStep = null;
      run.completedAt = nowIso();
      run.updatedAt = nowIso();
      syncSeriesSummary(seriesId);
      return;
    }

    run.status = "running";
    run.currentStep = step.stepIndex;
    step.status = "running";
    step.startedAt = nowIso();
    run.updatedAt = nowIso();
    syncSeriesSummary(seriesId);

    const completeTimeoutId = setTimeout(() => {
      const currentRun = getRuns(seriesId).find((item) => item.id === runId);
      if (!currentRun) {
        return;
      }
      const currentSeries = getSeries(seriesId);
      const currentStepState = currentRun.steps[stepIndex];
      const script = buildGeneratedScript(currentSeries, currentStepState.sequenceNumber);
      script.seriesRunId = currentRun.id;
      const scripts = getScripts(seriesId);
      scripts.push(script);
      state.scriptsBySeriesId.set(seriesId, scripts);

      currentStepState.seriesScriptId = script.id;
      currentStepState.status = "completed";
      currentStepState.outputPayload = { title: script.title, seriesScriptId: script.id };
      currentStepState.completedAt = nowIso();
      currentStepState.updatedAt = nowIso();
      currentRun.completedScriptCount += 1;
      currentRun.updatedAt = nowIso();

      if (stepIndex === currentRun.steps.length - 1) {
        currentRun.status = "completed";
        currentRun.currentStep = null;
        currentRun.completedAt = nowIso();
      } else {
        const nextStep = currentRun.steps[stepIndex + 1];
        currentRun.currentStep = nextStep.stepIndex;
        nextStep.status = "queued";
      }
      syncSeriesSummary(seriesId);
      if (stepIndex < currentRun.steps.length - 1) {
        queueNextStep(seriesId, runId, stepIndex + 1);
      }
    }, 550 + stepIndex * 180);

    state.timeoutsByRunId.set(runId, completeTimeoutId);
  }, stepIndex === 0 ? 300 : 250);

  state.timeoutsByRunId.set(runId, timeoutId);
}

function ensureEditable(seriesId: string): void {
  if (activeRun(seriesId)) {
    throw new ApiError(409, "series_locked", "Series cannot be edited while a run is queued or running.");
  }
}

export async function mockGetSeriesCatalog(): Promise<SeriesCatalog> {
  return clone(SERIES_CATALOG);
}

export async function mockGetSeriesList(): Promise<SeriesSummary[]> {
  return state.series
    .map((series) => summarize(series))
    .sort((a, b) => b.lastActivityAt.localeCompare(a.lastActivityAt))
    .map(clone);
}

export async function mockGetSeriesDetail(seriesId: string): Promise<SeriesDetail> {
  return clone(summarize(getSeries(seriesId)));
}

export async function mockCreateSeries(input: SeriesInput): Promise<SeriesDetail> {
  const createdAt = nowIso();
  const created: SeriesDetail = {
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
    latestRunId: null,
    latestRunStatus: null,
    activeRunId: null,
    activeRunStatus: null,
    canEdit: true,
    lastActivityAt: createdAt,
    createdAt,
    updatedAt: createdAt,
  };
  state.series.unshift(created);
  state.scriptsBySeriesId.set(created.id, []);
  state.runsBySeriesId.set(created.id, []);
  return clone(created);
}

export async function mockUpdateSeries(seriesId: string, input: SeriesInput): Promise<SeriesDetail> {
  ensureEditable(seriesId);
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
  syncSeriesSummary(seriesId);
  return clone(getSeries(seriesId));
}

export async function mockGetSeriesScripts(seriesId: string): Promise<SeriesScript[]> {
  return getScripts(seriesId)
    .slice()
    .sort((a, b) => a.sequenceNumber - b.sequenceNumber)
    .map(clone);
}

export async function mockStartSeriesRun(
  seriesId: string,
  requestedScriptCount: number,
  idempotencyKey: string,
): Promise<SeriesRun> {
  const existing = getRuns(seriesId).find((run) => run.idempotencyKey === idempotencyKey);
  if (existing) {
    return clone(existing);
  }
  if (activeRun(seriesId)) {
    throw new ApiError(409, "series_run_active", "This series already has a queued or running generation run.");
  }
  const series = getSeries(seriesId);
  const startSequence = getScripts(seriesId).length;
  const createdAt = nowIso();
  const run: SeriesRun = {
    id: nextId("series_run"),
    seriesId,
    workspaceId: series.workspaceId,
    createdByUserId: series.ownerUserId,
    status: "queued",
    requestedScriptCount,
    completedScriptCount: 0,
    failedScriptCount: 0,
    idempotencyKey,
    requestHash: idempotencyKey,
    payload: {},
    errorCode: null,
    errorMessage: null,
    retryCount: 0,
    startedAt: null,
    completedAt: null,
    cancelledAt: null,
    createdAt,
    updatedAt: createdAt,
    steps: Array.from({ length: requestedScriptCount }, (_, index) => ({
      id: nextId("series_step"),
      seriesRunId: "",
      seriesId,
      seriesScriptId: null,
      stepIndex: index + 1,
      sequenceNumber: startSequence + index + 1,
      status: "queued",
      inputPayload: { sequenceNumber: startSequence + index + 1 },
      outputPayload: null,
      errorCode: null,
      errorMessage: null,
      startedAt: null,
      completedAt: null,
      createdAt,
      updatedAt: createdAt,
    })),
    currentStep: 1,
  };
  run.steps.forEach((step) => {
    step.seriesRunId = run.id;
  });
  const runs = getRuns(seriesId);
  runs.unshift(run);
  state.runsBySeriesId.set(seriesId, runs);
  syncSeriesSummary(seriesId);
  queueNextStep(seriesId, run.id, 0);
  return clone(run);
}

export async function mockGetSeriesRun(seriesId: string, runId: string): Promise<SeriesRun> {
  const run = getRuns(seriesId).find((item) => item.id === runId);
  if (!run) {
    throw new ApiError(404, "series_run_not_found", "Series run not found.");
  }
  return clone(run);
}
