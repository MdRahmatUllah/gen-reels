import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { EmptyState, MetricCard, PageFrame, ProgressBar, SectionCard, StatusBadge } from "../../components/ui";
import { relativeTime, titleFromStatus } from "../../lib/format";
import {
  useCreateSeries,
  useSeriesCatalog,
  useSeriesDetail,
  useSeriesList,
  useSeriesRun,
  useSeriesScripts,
  useStartSeriesRun,
  useUpdateSeries,
} from "../../hooks/use-series";
import type {
  SeriesCatalog,
  SeriesCatalogOption,
  SeriesDetail,
  SeriesInput,
  SeriesRun,
  SeriesScript,
} from "../../types/domain";

const SERIES_STEPS = [
  "Overview & Topic",
  "Language & Voice",
  "Background Music",
  "Art Style",
  "Caption Style",
  "Effects",
];

type SeriesTab = "scripts" | "videos";

function buildDefaultInput(catalog: SeriesCatalog): SeriesInput {
  return {
    title: "",
    description: "",
    contentMode: "preset",
    presetKey: catalog.contentPresets[0]?.key ?? null,
    customTopic: "",
    customExampleScript: "",
    languageKey: catalog.languages[0]?.key ?? "en",
    voiceKey: catalog.voices[0]?.key ?? "",
    musicMode: "none",
    musicKeys: [],
    artStyleKey: catalog.artStyles[0]?.key ?? "",
    captionStyleKey: catalog.captionStyles[0]?.key ?? "",
    effectKeys: [],
  };
}

function applySeriesDetail(detail: SeriesDetail): SeriesInput {
  return {
    title: detail.title,
    description: detail.description,
    contentMode: detail.contentMode,
    presetKey: detail.presetKey,
    customTopic: detail.customTopic,
    customExampleScript: detail.customExampleScript,
    languageKey: detail.languageKey,
    voiceKey: detail.voiceKey,
    musicMode: detail.musicMode,
    musicKeys: [...detail.musicKeys],
    artStyleKey: detail.artStyleKey,
    captionStyleKey: detail.captionStyleKey,
    effectKeys: [...detail.effectKeys],
  };
}

function lookupOption(options: SeriesCatalogOption[], key: string | null | undefined): SeriesCatalogOption | null {
  return options.find((option) => option.key === key) ?? null;
}

function optionButtonClass(selected: boolean) {
  return selected
    ? "rounded-xl border border-border-active bg-primary-bg p-4 text-left shadow-sm transition-all"
    : "rounded-xl border border-border-card bg-card p-4 text-left transition-all hover:border-border-active";
}

function SeriesOptionButton({
  option,
  selected,
  onClick,
  disabled = false,
}: {
  option: SeriesCatalogOption;
  selected: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`${optionButtonClass(selected)} ${disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <strong className="text-sm text-primary">{option.label}</strong>
            {option.badge ? (
              <span className="rounded-full bg-glass px-2 py-0.5 text-[0.65rem] font-semibold text-muted">
                {option.badge}
              </span>
            ) : null}
          </div>
          {option.gender ? <p className="mt-1 text-xs text-muted">{option.gender}</p> : null}
        </div>
        {selected ? <span className="text-xs font-semibold text-accent">Selected</span> : null}
      </div>
      <p className="mt-2 text-sm leading-6 text-secondary">{option.description}</p>
    </button>
  );
}

function StepPills({ step }: { step: number }) {
  return (
    <div className="flex flex-wrap gap-2">
      {SERIES_STEPS.map((label, index) => (
        <div
          key={label}
          className={
            index === step
              ? "rounded-full bg-primary-bg px-3 py-1 text-xs font-semibold text-primary"
              : "rounded-full bg-glass px-3 py-1 text-xs font-medium text-muted"
          }
        >
          {index + 1}. {label}
        </div>
      ))}
    </div>
  );
}

function SeriesRunPanel({ run }: { run: SeriesRun }) {
  const progress = run.requestedScriptCount
    ? (run.completedScriptCount / run.requestedScriptCount) * 100
    : 0;
  return (
    <SectionCard
      title="Current Run"
      subtitle={`Generating ${run.requestedScriptCount} script${run.requestedScriptCount === 1 ? "" : "s"} sequentially.`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">Status</p>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge status={run.status} />
            {run.errorMessage ? <span className="text-sm text-error">{run.errorMessage}</span> : null}
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-widest text-muted">Progress</p>
          <p className="mt-1 text-sm font-semibold text-primary">
            {run.completedScriptCount} / {run.requestedScriptCount}
          </p>
        </div>
      </div>
      <ProgressBar
        value={progress}
        label="Scripts generated"
        detail={run.currentStep ? `Currently processing step ${run.currentStep}` : "Waiting for the next update."}
      />
      <div className="grid gap-3">
        {run.steps.map((step) => (
          <div key={step.id} className="rounded-xl border border-border-card bg-card px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-widest text-muted">Script {step.sequenceNumber}</p>
                <strong className="text-sm text-primary">Step {step.stepIndex}</strong>
              </div>
              <StatusBadge status={step.status} />
            </div>
            {step.errorMessage ? <p className="mt-2 text-sm text-error">{step.errorMessage}</p> : null}
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function SeriesScriptCard({
  script,
  expanded,
  onToggle,
}: {
  script: SeriesScript;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <section className="rounded-2xl border border-border-card bg-card p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">Script {script.sequenceNumber}</p>
          <h3 className="mt-1 font-heading text-xl font-bold text-primary">{script.title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-secondary">{script.summary}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-glass px-3 py-1 text-xs font-medium text-muted">
            {script.readingTimeLabel}
          </span>
          <button type="button" className="btn-ghost !min-h-[2.2rem]" onClick={onToggle}>
            {expanded ? "Hide outline" : "Preview outline"}
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted">
        <span className="rounded-full bg-glass px-3 py-1">{script.totalWords} words</span>
        <span className="rounded-full bg-glass px-3 py-1">{script.estimatedDurationSeconds}s estimated</span>
        <span className="rounded-full bg-glass px-3 py-1">{relativeTime(script.createdAt)}</span>
      </div>
      {expanded ? (
        <div className="mt-5 grid gap-3">
          {script.lines.map((line, index) => (
            <div key={line.id} className="rounded-xl border border-border-card bg-glass p-4">
              <div className="flex items-center justify-between gap-3">
                <strong className="text-sm text-primary">
                  {index + 1}. {line.beat}
                </strong>
                <span className="text-xs text-muted">{line.durationSec}s</span>
              </div>
              <p className="mt-2 text-sm leading-6 text-secondary">{line.narration}</p>
              <p className="mt-2 text-xs uppercase tracking-widest text-muted">{line.caption}</p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SeriesStartDialog({
  open,
  count,
  onCountChange,
  pending,
  onClose,
  onStart,
}: {
  open: boolean;
  count: number;
  onCountChange: (value: number) => void;
  pending: boolean;
  onClose: () => void;
  onStart: () => void;
}) {
  if (!open) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 py-8 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-border-card bg-surface p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-muted">Start Series</p>
            <h3 className="mt-1 font-heading text-2xl font-bold text-primary">How many scripts should we generate?</h3>
          </div>
          <button type="button" className="btn-ghost !min-h-[2rem]" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mt-6">
          <label className="text-sm font-semibold text-primary" htmlFor="series-script-count">
            Requested script count
          </label>
          <input
            id="series-script-count"
            type="number"
            min={1}
            max={50}
            value={count}
            onChange={(event) => onCountChange(Number(event.target.value))}
            className="mt-2 w-full rounded-xl border border-border-card bg-card px-4 py-3 text-base text-primary outline-none transition-all focus:border-border-active"
          />
          <p className="mt-2 text-sm text-secondary">
            Scripts are generated one by one, and new scripts will append to the existing series library.
          </p>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" className="btn-ghost" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={onStart} disabled={pending}>
            {pending ? "Starting..." : "Start generation"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function SeriesListPage() {
  const { data: series = [], isLoading } = useSeriesList();

  if (isLoading) {
    return (
      <PageFrame eyebrow="Series" title="Loading series" description="Preparing your series workspace." inspector={<SectionCard title="Loading"><div className="h-32 rounded-xl bg-glass" /></SectionCard>}>
        <SectionCard title="Loading">
          <div className="h-64 rounded-xl bg-glass" />
        </SectionCard>
      </PageFrame>
    );
  }

  return (
    <PageFrame
      eyebrow="Series"
      title="Repeatable content systems"
      description="Create a reusable content series, lock in the topic and style, then keep generating fresh scripts that stack inside one shared series library."
      actions={
        <Link className="btn-primary" to="/app/series/new">
          Create Series
        </Link>
      }
      inspector={
        <div className="inspector-stack">
          <MetricCard label="Total series" value={String(series.length)} detail="Saved content systems in this workspace." tone="primary" />
          <MetricCard label="Active runs" value={String(series.filter((item) => item.activeRunStatus).length)} detail="Series currently generating scripts." tone="neutral" />
          <SectionCard title="How it works">
            <p className="text-sm leading-6 text-secondary">
              Each series stores one repeatable storytelling setup. Starting a series creates a run that generates scripts one by one and appends them to the Scripts tab.
            </p>
          </SectionCard>
        </div>
      }
    >
      {series.length === 0 ? (
        <EmptyState
          title="No series yet"
          description="Create your first series to save a repeatable storytelling setup and start generating scripts on demand."
        />
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {series.map((item) => (
            <Link key={item.id} to={`/app/series/${item.id}`} className="rounded-2xl border border-border-card bg-card p-5 shadow-card transition-all hover:border-border-active hover:-translate-y-0.5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-widest text-muted">
                    {item.contentMode === "preset" ? "Preset series" : "Custom series"}
                  </p>
                  <h3 className="mt-1 font-heading text-xl font-bold text-primary">{item.title}</h3>
                </div>
                {item.latestRunStatus ? <StatusBadge status={item.latestRunStatus} /> : null}
              </div>
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-secondary">{item.description || "No short description yet."}</p>
              <div className="mt-5 flex flex-wrap gap-2 text-xs text-muted">
                <span className="rounded-full bg-glass px-3 py-1">{item.totalScriptCount} scripts</span>
                <span className="rounded-full bg-glass px-3 py-1">{relativeTime(item.lastActivityAt)}</span>
                <span className="rounded-full bg-glass px-3 py-1">{titleFromStatus(item.voiceKey)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </PageFrame>
  );
}

export function SeriesEditorPage() {
  const navigate = useNavigate();
  const params = useParams();
  const seriesId = params.seriesId ?? "";
  const isEditing = Boolean(seriesId);
  const { data: catalog, isLoading: catalogLoading } = useSeriesCatalog();
  const detailQuery = useSeriesDetail(seriesId);
  const createMutation = useCreateSeries();
  const updateMutation = useUpdateSeries(seriesId);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<SeriesInput | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!catalog || initialized) {
      return;
    }
    if (isEditing) {
      if (detailQuery.data) {
        setForm(applySeriesDetail(detailQuery.data));
        setInitialized(true);
      }
      return;
    }
    setForm(buildDefaultInput(catalog));
    setInitialized(true);
  }, [catalog, detailQuery.data, initialized, isEditing]);

  const pending = createMutation.isPending || updateMutation.isPending;

  const summaryBits = useMemo(() => {
    if (!catalog || !form) {
      return [];
    }
    return [
      lookupOption(catalog.contentPresets, form.presetKey)?.label || "Custom topic",
      lookupOption(catalog.voices, form.voiceKey)?.label || "Voice",
      lookupOption(catalog.artStyles, form.artStyleKey)?.label || "Art style",
      lookupOption(catalog.captionStyles, form.captionStyleKey)?.label || "Caption style",
    ];
  }, [catalog, form]);

  if (catalogLoading || !catalog || !form || (isEditing && detailQuery.isLoading && !detailQuery.data)) {
    return (
      <PageFrame eyebrow="Series" title="Loading editor" description="Preparing the series wizard." inspector={<SectionCard title="Loading"><div className="h-32 rounded-xl bg-glass" /></SectionCard>}>
        <SectionCard title="Loading">
          <div className="h-64 rounded-xl bg-glass" />
        </SectionCard>
      </PageFrame>
    );
  }

  function updateForm(partial: Partial<SeriesInput>) {
    setForm((current) => (current ? { ...current, ...partial } : current));
  }

  function toggleMultiValue(field: "musicKeys" | "effectKeys", key: string) {
    setForm((current) => {
      if (!current) {
        return current;
      }
      const hasKey = current[field].includes(key);
      return {
        ...current,
        [field]: hasKey ? current[field].filter((value) => value !== key) : [...current[field], key],
      };
    });
  }

  async function saveSeries() {
    const currentForm = form;
    if (!currentForm) {
      return;
    }
    if (!currentForm.title.trim()) {
      setErrorMessage("Series title is required.");
      setStep(0);
      return;
    }
    if (currentForm.contentMode === "custom" && !currentForm.customTopic.trim()) {
      setErrorMessage("Describe your custom niche before saving the series.");
      setStep(0);
      return;
    }
    if (currentForm.musicMode === "preset" && currentForm.musicKeys.length === 0) {
      setErrorMessage("Pick at least one music option or switch to None.");
      setStep(2);
      return;
    }
    setErrorMessage(null);
    const mutation = isEditing ? updateMutation : createMutation;
    try {
      const saved = await mutation.mutateAsync(currentForm);
      navigate(`/app/series/${saved.id}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to save the series right now.");
    }
  }

  const stepContent = [
    <SectionCard key="overview" title="Overview & Topic" subtitle="Define the series identity and pick a preset or custom niche.">
      <div className="grid gap-5">
        <div>
          <label className="text-sm font-semibold text-primary" htmlFor="series-title">Title</label>
          <input
            id="series-title"
            value={form.title}
            onChange={(event) => updateForm({ title: event.target.value })}
            className="mt-2 w-full rounded-xl border border-border-card bg-card px-4 py-3 text-base text-primary outline-none transition-all focus:border-border-active"
            placeholder="Series title"
          />
        </div>
        <div>
          <label className="text-sm font-semibold text-primary" htmlFor="series-description">Short details</label>
          <textarea
            id="series-description"
            value={form.description}
            onChange={(event) => updateForm({ description: event.target.value })}
            className="mt-2 min-h-28 w-full rounded-xl border border-border-card bg-card px-4 py-3 text-base text-primary outline-none transition-all focus:border-border-active"
            placeholder="A short summary of the series."
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={form.contentMode === "preset" ? "chip-button chip-button--active" : "chip-button"} onClick={() => updateForm({ contentMode: "preset" })}>Use preset</button>
          <button type="button" className={form.contentMode === "custom" ? "chip-button chip-button--active" : "chip-button"} onClick={() => updateForm({ contentMode: "custom" })}>Custom niche</button>
        </div>
        {form.contentMode === "preset" ? (
          <div className="grid gap-3 md:grid-cols-2">
            {catalog.contentPresets.map((option) => (
              <SeriesOptionButton key={option.key} option={option} selected={form.presetKey === option.key} onClick={() => updateForm({ presetKey: option.key })} />
            ))}
          </div>
        ) : (
          <div className="grid gap-5">
            <div>
              <label className="text-sm font-semibold text-primary" htmlFor="custom-topic">Describe your topic</label>
              <textarea
                id="custom-topic"
                value={form.customTopic}
                onChange={(event) => updateForm({ customTopic: event.target.value })}
                className="mt-2 min-h-40 w-full rounded-xl border border-border-card bg-card px-4 py-3 text-base text-primary outline-none transition-all focus:border-border-active"
                placeholder="Describe the content focus and the angle you want each video to take."
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-primary" htmlFor="example-script">Example script</label>
              <textarea
                id="example-script"
                value={form.customExampleScript}
                onChange={(event) => updateForm({ customExampleScript: event.target.value })}
                className="mt-2 min-h-36 w-full rounded-xl border border-border-card bg-card px-4 py-3 text-base text-primary outline-none transition-all focus:border-border-active"
                placeholder="Paste an example of how you want your videos to sound."
              />
            </div>
          </div>
        )}
      </div>
    </SectionCard>,
    <SectionCard key="voice" title="Language & Voice" subtitle="Choose the language and narration style for the series.">
      <div className="grid gap-5">
        <div className="grid gap-3 md:grid-cols-2">
          {catalog.languages.map((option) => (
            <SeriesOptionButton key={option.key} option={option} selected={form.languageKey === option.key} onClick={() => updateForm({ languageKey: option.key })} />
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {catalog.voices.map((option) => (
            <SeriesOptionButton key={option.key} option={option} selected={form.voiceKey === option.key} onClick={() => updateForm({ voiceKey: option.key })} />
          ))}
        </div>
      </div>
    </SectionCard>,
    <SectionCard key="music" title="Background Music" subtitle="Choose preset music or leave the series without music for now.">
      <div className="grid gap-5">
        <div className="flex flex-wrap gap-2">
          <button type="button" className={form.musicMode === "none" ? "chip-button chip-button--active" : "chip-button"} onClick={() => updateForm({ musicMode: "none", musicKeys: [] })}>None</button>
          <button type="button" className={form.musicMode === "preset" ? "chip-button chip-button--active" : "chip-button"} onClick={() => updateForm({ musicMode: "preset" })}>Preset music</button>
          <button type="button" className="chip-button opacity-50 cursor-not-allowed" disabled>Custom coming soon</button>
        </div>
        {form.musicMode === "preset" ? (
          <div className="grid gap-3 md:grid-cols-2">
            {catalog.music.map((option) => (
              <SeriesOptionButton key={option.key} option={option} selected={form.musicKeys.includes(option.key)} onClick={() => toggleMultiValue("musicKeys", option.key)} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border-card bg-card p-6">
            <p className="text-sm leading-6 text-secondary">
              This series will be saved without background music. You can add video-side audio behavior later when the video generation phase is ready.
            </p>
          </div>
        )}
      </div>
    </SectionCard>,
  ];

  stepContent.push(
    <SectionCard key="art" title="Art Style" subtitle="Set the visual language used for the generated script prompts.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {catalog.artStyles.map((option) => (
          <SeriesOptionButton key={option.key} option={option} selected={form.artStyleKey === option.key} onClick={() => updateForm({ artStyleKey: option.key })} />
        ))}
      </div>
    </SectionCard>,
  );
  stepContent.push(
    <SectionCard key="caption" title="Caption Style" subtitle="Choose how captions will appear in the generated videos later on.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {catalog.captionStyles.map((option) => (
          <SeriesOptionButton key={option.key} option={option} selected={form.captionStyleKey === option.key} onClick={() => updateForm({ captionStyleKey: option.key })} />
        ))}
      </div>
    </SectionCard>,
  );
  stepContent.push(
    <SectionCard key="effects" title="Effects" subtitle="Optional visual effects that shape the future video treatment.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {catalog.effects.map((option) => (
          <SeriesOptionButton key={option.key} option={option} selected={form.effectKeys.includes(option.key)} onClick={() => toggleMultiValue("effectKeys", option.key)} />
        ))}
      </div>
    </SectionCard>,
  );

  return (
    <PageFrame
      eyebrow="Series"
      title={isEditing ? "Edit series" : "Create a new series"}
      description="Build a reusable series definition in six steps. Once saved, you can start runs that generate scripts one by one into the same series library."
      actions={
        <>
          <button type="button" className="btn-ghost" onClick={() => navigate(isEditing ? `/app/series/${seriesId}` : "/app/series")}>Cancel</button>
          <button type="button" className="btn-primary" disabled={pending} onClick={saveSeries}>
            {pending ? "Saving..." : isEditing ? "Save changes" : "Create series"}
          </button>
        </>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title={`Step ${step + 1} of ${SERIES_STEPS.length}`}>
            <StepPills step={step} />
          </SectionCard>
          <SectionCard title="Series summary">
            <div className="inspector-list">
              <div>
                <span>Title</span>
                <strong>{form.title || "Untitled series"}</strong>
              </div>
              <div>
                <span>Mode</span>
                <strong>{form.contentMode === "preset" ? "Preset" : "Custom niche"}</strong>
              </div>
              <div>
                <span>Selections</span>
                <strong>{summaryBits.join(" · ")}</strong>
              </div>
            </div>
          </SectionCard>
          {errorMessage ? (
            <SectionCard title="Needs attention">
              <p className="text-sm leading-6 text-error">{errorMessage}</p>
            </SectionCard>
          ) : null}
        </div>
      }
    >
      {stepContent[step]}
      <div className="flex flex-wrap justify-between gap-3">
        <button type="button" className="btn-ghost" disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))}>Previous step</button>
        <button type="button" className="btn-primary" onClick={() => setStep((current) => Math.min(SERIES_STEPS.length - 1, current + 1))} disabled={step === SERIES_STEPS.length - 1}>Next step</button>
      </div>
    </PageFrame>
  );
}

export function SeriesDetailPage() {
  const params = useParams();
  const seriesId = params.seriesId ?? "";
  const { data: catalog, isLoading: catalogLoading } = useSeriesCatalog();
  const detailQuery = useSeriesDetail(seriesId);
  const scriptsQuery = useSeriesScripts(seriesId);
  const [activeTab, setActiveTab] = useState<SeriesTab>("scripts");
  const [expandedScripts, setExpandedScripts] = useState<Record<string, boolean>>({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [requestedScriptCount, setRequestedScriptCount] = useState(5);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const startRunMutation = useStartSeriesRun(seriesId);
  const runId = selectedRunId ?? detailQuery.data?.activeRunId ?? detailQuery.data?.latestRunId ?? null;
  const runQuery = useSeriesRun(seriesId, runId);

  useEffect(() => {
    if (detailQuery.data?.activeRunId) {
      setSelectedRunId(detailQuery.data.activeRunId);
    }
  }, [detailQuery.data?.activeRunId]);

  if (catalogLoading || detailQuery.isLoading || !detailQuery.data || !catalog) {
    return (
      <PageFrame eyebrow="Series" title="Loading series" description="Preparing the series detail view." inspector={<SectionCard title="Loading"><div className="h-32 rounded-xl bg-glass" /></SectionCard>}>
        <SectionCard title="Loading">
          <div className="h-64 rounded-xl bg-glass" />
        </SectionCard>
      </PageFrame>
    );
  }

  const series = detailQuery.data;
  const scripts = scriptsQuery.data ?? [];
  const contentOption = series.contentMode === "preset" ? lookupOption(catalog.contentPresets, series.presetKey) : null;

  async function handleStart() {
    const safeCount = Math.max(1, Math.min(50, requestedScriptCount));
    const run = await startRunMutation.mutateAsync({ requestedScriptCount: safeCount, idempotencyKey });
    setSelectedRunId(run.id);
    setDialogOpen(false);
  }

  return (
    <>
      <SeriesStartDialog open={dialogOpen} count={requestedScriptCount} onCountChange={setRequestedScriptCount} pending={startRunMutation.isPending} onClose={() => setDialogOpen(false)} onStart={() => void handleStart()} />
      <PageFrame
        eyebrow="Series"
        title={series.title}
        description={series.description || "A saved content series ready for repeatable script generation."}
        actions={
          <>
            <Link className="btn-ghost" to="/app/series">Back to series</Link>
            <Link className={series.canEdit ? "btn-ghost" : "btn-ghost opacity-50 pointer-events-none"} to={`/app/series/${series.id}/edit`}>Edit</Link>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setRequestedScriptCount(5);
                setIdempotencyKey(crypto.randomUUID());
                setDialogOpen(true);
              }}
              disabled={Boolean(series.activeRunId)}
            >
              {series.activeRunId ? "Run in progress" : "Start series"}
            </button>
          </>
        }
        inspector={
          <div className="inspector-stack">
            <MetricCard label="Scripts" value={String(series.totalScriptCount)} detail="Generated scripts stored in this series." tone="primary" />
            <MetricCard label="Last activity" value={relativeTime(series.lastActivityAt)} detail={series.latestRunStatus ? `Latest run ${titleFromStatus(series.latestRunStatus)}` : "No runs yet"} tone="neutral" />
            <SectionCard title="Configuration">
              <div className="inspector-list">
                <div><span>Topic</span><strong>{contentOption?.label ?? "Custom niche"}</strong></div>
                <div><span>Voice</span><strong>{lookupOption(catalog.voices, series.voiceKey)?.label ?? series.voiceKey}</strong></div>
                <div><span>Art style</span><strong>{lookupOption(catalog.artStyles, series.artStyleKey)?.label ?? series.artStyleKey}</strong></div>
                <div><span>Caption style</span><strong>{lookupOption(catalog.captionStyles, series.captionStyleKey)?.label ?? series.captionStyleKey}</strong></div>
              </div>
            </SectionCard>
          </div>
        }
      >
        {series.contentMode === "custom" ? (
          <SectionCard title="Custom niche" subtitle="This series uses a custom topic and optional style reference.">
            <p className="text-sm leading-6 text-secondary">{series.customTopic}</p>
            {series.customExampleScript ? (
              <div className="rounded-2xl border border-border-card bg-glass p-4 text-sm leading-6 text-secondary">{series.customExampleScript}</div>
            ) : null}
          </SectionCard>
        ) : (
          <SectionCard title="Selected preset" subtitle={contentOption?.description ?? "Using a preset-backed topic definition."}>
            <p className="text-sm leading-6 text-secondary">{contentOption?.label}</p>
          </SectionCard>
        )}

        {runQuery.data ? <SeriesRunPanel run={runQuery.data} /> : null}

        <div className="flex flex-wrap gap-2">
          <button type="button" className={activeTab === "scripts" ? "chip-button chip-button--active" : "chip-button"} onClick={() => setActiveTab("scripts")}>Scripts</button>
          <button type="button" className={activeTab === "videos" ? "chip-button chip-button--active" : "chip-button"} onClick={() => setActiveTab("videos")}>Videos</button>
        </div>

        {activeTab === "scripts" ? (
          scripts.length === 0 ? (
            <EmptyState title="No scripts yet" description="Start the series to generate scripts one by one. Each new run appends more scripts into this tab." />
          ) : (
            <div className="grid gap-5">
              {scripts.map((script) => (
                <SeriesScriptCard key={script.id} script={script} expanded={Boolean(expandedScripts[script.id])} onToggle={() => setExpandedScripts((current) => ({ ...current, [script.id]: !current[script.id] }))} />
              ))}
            </div>
          )
        ) : (
          <EmptyState title="Videos are coming next" description="Series videos will appear here in the next phase. For now, this version stops after generating scripts." />
        )}
      </PageFrame>
    </>
  );
}
