import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dialog } from "../../components/Dialog";
import { LoadingPage, SectionCard, StatusBadge } from "../../components/ui";
import {
  mockGetRemixProjects,
  mockCreateRemixProject,
  mockDeleteRemixProject,
  mockAnalyzeRemixProject,
  mockCreateRemixJob,
  mockGetRemixJob,
  mockListRemixJobs,
  mockStopRemixJob,
  mockGetVideoLibraryProjects,
} from "../../lib/mock-service";
import type {
  RemixProject,
  RemixJob,
  VideoLibraryProject,
} from "../../types/domain";

/* ─── Icons ───────────────────────────────────────────────────────────────── */
function PlusIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function PlayIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

function TrashIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
    </svg>
  );
}

function StopIcon({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
    </svg>
  );
}

function RemixIcon({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function CheckIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

/* ─── Helpers ─────────────────────────────────────────────────────────────── */
function formatDuration(ms: number): string {
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

const EFFECT_OPTIONS = [
  { value: "none", label: "None" },
  { value: "warm", label: "Warm" },
  { value: "cool", label: "Cool" },
  { value: "sepia", label: "Sepia" },
  { value: "grayscale", label: "Grayscale" },
  { value: "vintage", label: "Vintage" },
  { value: "vibrant", label: "Vibrant" },
  { value: "moody", label: "Moody" },
];

const DURATION_PRESETS = [
  { label: "15s", ms: 15_000 },
  { label: "30s", ms: 30_000 },
  { label: "45s", ms: 45_000 },
  { label: "60s", ms: 60_000 },
  { label: "90s", ms: 90_000 },
];

/* ─── Remix Progress Bar ──────────────────────────────────────────────────── */
function RemixProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="h-1.5 w-full bg-border-subtle rounded-full overflow-hidden">
      <div
        className="h-full rounded-full bg-accent-gradient transition-all duration-500 ease-out"
        style={{ width: `${pct}%`, boxShadow: pct > 0 ? "0 0 8px var(--accent-glow)" : "none" }}
      />
    </div>
  );
}

/* ─── Create Wizard Dialog ───────────────────────────────────────────────── */
type WizardStep = "name" | "source" | "effects" | "duration" | "mode";

interface WizardState {
  name: string;
  source_project_id: string | null;
  color_filter: string;
  brightness: number;
  contrast: number;
  saturation: number;
  fade_in_sec: number;
  fade_out_sec: number;
  vignette_strength: number;
  target_duration_ms: number;
  clip_mode: "random" | "unique";
}

const DEFAULT_WIZARD: WizardState = {
  name: "",
  source_project_id: null,
  color_filter: "none",
  brightness: 0,
  contrast: 0,
  saturation: 0,
  fade_in_sec: 0,
  fade_out_sec: 0,
  vignette_strength: 0,
  target_duration_ms: 30_000,
  clip_mode: "random",
};

function CreateWizardDialog({
  open,
  videoLibraryProjects,
  onClose,
  onCreated,
}: {
  open: boolean;
  videoLibraryProjects: VideoLibraryProject[];
  onClose: () => void;
  onCreated: (project: RemixProject) => void;
}) {
  const [step, setStep] = useState<WizardStep>("name");
  const [form, setForm] = useState<WizardState>(DEFAULT_WIZARD);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setStep("name");
      setForm(DEFAULT_WIZARD);
      setError("");
    }
  }, [open]);

  const createMutation = useMutation({
    mutationFn: () =>
      mockCreateRemixProject({
        name: form.name.trim(),
        source_project_id: form.source_project_id,
        visual_effects: {
          color_filter: form.color_filter,
          brightness: form.brightness,
          contrast: form.contrast,
          saturation: form.saturation,
          fade_in_sec: form.fade_in_sec,
          fade_out_sec: form.fade_out_sec,
          vignette_strength: form.vignette_strength,
        },
        target_duration_ms: form.target_duration_ms,
        clip_mode: form.clip_mode,
      }),
    onSuccess: (project) => onCreated(project),
    onError: (e: Error) => setError(e.message),
  });

  const STEPS: WizardStep[] = ["name", "source", "effects", "duration", "mode"];
  const stepIndex = STEPS.indexOf(step);
  const isLast = step === "mode";

  function next() {
    if (step === "name" && !form.name.trim()) {
      setError("Please enter a project name.");
      return;
    }
    setError("");
    if (isLast) {
      createMutation.mutate();
    } else {
      setStep(STEPS[stepIndex + 1]);
    }
  }

  function back() {
    if (stepIndex > 0) {
      setError("");
      setStep(STEPS[stepIndex - 1]);
    }
  }

  const stepLabel: Record<WizardStep, string> = {
    name: "Project Name",
    source: "Source Folder",
    effects: "Visual Effects",
    duration: "Target Duration",
    mode: "Clip Mode",
  };

  return (
    <Dialog open={open} title="Create Remix Project" onClose={onClose}>
      {/* Step indicator */}
      <div className="flex gap-1 mb-6">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`remix-wizard-step ${i <= stepIndex ? "bg-accent" : "bg-border-subtle"}`}
          />
        ))}
      </div>

      <p className="text-[0.6875rem] tracking-widest uppercase font-bold text-muted mb-4">
        Step {stepIndex + 1} of {STEPS.length} — {stepLabel[step]}
      </p>

      {/* Step: Name */}
      {step === "name" && (
        <div>
          <input
            autoFocus
            type="text"
            className="field-input"
            placeholder="e.g. Summer Travel Mix"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && next()}
          />
        </div>
      )}

      {/* Step: Source folder */}
      {step === "source" && (
        <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
          <button
            className={`remix-option ${form.source_project_id === null ? "remix-option--active" : "remix-option--inactive"}`}
            onClick={() => setForm({ ...form, source_project_id: null })}
          >
            <div className="font-semibold text-sm text-primary">No Project</div>
            <div className="text-xs text-secondary mt-0.5">Clips not assigned to any project</div>
          </button>
          {videoLibraryProjects.map((p) => (
            <button
              key={p.id}
              className={`remix-option ${form.source_project_id === p.id ? "remix-option--active" : "remix-option--inactive"}`}
              onClick={() => setForm({ ...form, source_project_id: p.id })}
            >
              <div className="font-semibold text-sm text-primary">{p.name}</div>
              {p.description && <div className="text-xs text-secondary mt-0.5">{p.description}</div>}
            </button>
          ))}
          {videoLibraryProjects.length === 0 && (
            <p className="text-sm text-muted text-center py-4">
              No projects in Video Library yet. "No Project" will use unassigned clips.
            </p>
          )}
        </div>
      )}

      {/* Step: Effects */}
      {step === "effects" && (
        <div className="flex flex-col gap-4">
          <div>
            <label className="text-[0.6875rem] tracking-widest uppercase font-bold text-muted mb-2 block">Color filter</label>
            <div className="grid grid-cols-4 gap-1.5">
              {EFFECT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={`chip-button ${form.color_filter === opt.value ? "chip-button--active" : ""}`}
                  onClick={() => setForm({ ...form, color_filter: opt.value })}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {(
              [
                ["brightness", "Brightness", -50, 50],
                ["contrast", "Contrast", -50, 50],
                ["saturation", "Saturation", -50, 50],
              ] as [keyof WizardState, string, number, number][]
            ).map(([key, label, min, max]) => (
              <div key={key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted">{label}</label>
                  <span className="text-xs font-semibold text-primary tabular-nums">{form[key] as number}</span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  value={form[key] as number}
                  onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
                  className="w-full accent-[var(--accent)] h-1.5 rounded-full appearance-none bg-border-subtle cursor-pointer"
                />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: "fade_in_sec" as const, label: "Fade in", max: 3, step: 0.5, unit: "s" },
              { key: "fade_out_sec" as const, label: "Fade out", max: 3, step: 0.5, unit: "s" },
              { key: "vignette_strength" as const, label: "Vignette", max: 100, step: 5, unit: "" },
            ].map((ctrl) => (
              <div key={ctrl.key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted">{ctrl.label}</label>
                  <span className="text-xs font-semibold text-primary tabular-nums">{form[ctrl.key]}{ctrl.unit}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={ctrl.max}
                  step={ctrl.step}
                  value={form[ctrl.key]}
                  onChange={(e) => setForm({ ...form, [ctrl.key]: Number(e.target.value) })}
                  className="w-full accent-[var(--accent)] h-1.5 rounded-full appearance-none bg-border-subtle cursor-pointer"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step: Duration */}
      {step === "duration" && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-5 gap-2">
            {DURATION_PRESETS.map((p) => (
              <button
                key={p.ms}
                className={`chip-button ${form.target_duration_ms === p.ms ? "chip-button--active" : ""}`}
                style={{ padding: "0.6rem 0" }}
                onClick={() => setForm({ ...form, target_duration_ms: p.ms })}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="form-field">
            <label className="text-[0.6875rem] tracking-widest uppercase font-bold text-muted">Custom (seconds)</label>
            <input
              type="number"
              min={5}
              max={600}
              className="field-input"
              value={Math.round(form.target_duration_ms / 1000)}
              onChange={(e) => {
                const secs = Math.max(5, Math.min(600, Number(e.target.value)));
                setForm({ ...form, target_duration_ms: secs * 1000 });
              }}
            />
          </div>
          <p className="text-xs text-muted">
            Videos may be slightly shorter or longer depending on clip lengths.
          </p>
        </div>
      )}

      {/* Step: Mode */}
      {step === "mode" && (
        <div className="flex flex-col gap-3">
          {[
            {
              value: "random" as const,
              title: "Random Clip",
              desc: "Clips can be reused across videos. Each video starts with a unique first clip. Maximises output volume.",
            },
            {
              value: "unique" as const,
              title: "Unique Clip",
              desc: "No clip appears in more than one video. Every video is completely distinct. Video count limited by footage.",
            },
          ].map((opt) => (
            <button
              key={opt.value}
              className={`remix-option ${form.clip_mode === opt.value ? "remix-option--active" : "remix-option--inactive"}`}
              style={{ padding: "1rem" }}
              onClick={() => setForm({ ...form, clip_mode: opt.value })}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-primary text-sm">{opt.title}</span>
                {form.clip_mode === opt.value && (
                  <span className="inline-flex items-center gap-1 text-success text-xs font-bold">
                    <CheckIcon size={12} />
                    Selected
                  </span>
                )}
              </div>
              <p className="text-xs text-secondary leading-relaxed">{opt.desc}</p>
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-error mt-3">{error}</p>}

      {/* Footer nav */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-border-subtle">
        <button
          className="text-sm text-secondary hover:text-primary transition-colors disabled:opacity-40"
          onClick={back}
          disabled={stepIndex === 0}
          type="button"
        >
          Back
        </button>
        <button
          className="btn-primary"
          onClick={next}
          disabled={createMutation.isPending}
          type="button"
        >
          {isLast
            ? createMutation.isPending
              ? "Creating..."
              : "Create project"
            : "Continue"}
        </button>
      </div>
    </Dialog>
  );
}

/* ─── Job Row ─────────────────────────────────────────────────────────────── */
const STALE_PENDING_MS = 5 * 60 * 1000;

function JobRow({ initialJob }: { initialJob: RemixJob }) {
  const qc = useQueryClient();
  const [job, setJob] = useState(initialJob);

  useEffect(() => {
    setJob(initialJob);
  }, [initialJob]);

  const isActive = job.status === "running" || job.status === "pending";
  const isStale =
    isActive &&
    Date.now() - new Date(job.created_at).getTime() > STALE_PENDING_MS &&
    job.completed_videos === 0;

  useEffect(() => {
    if (!isActive || isStale) return;
    const id = setInterval(async () => {
      try {
        const updated = await mockGetRemixJob(job.id);
        setJob(updated);
        if (updated.status === "completed" || updated.status === "failed" || updated.status === "cancelled") {
          clearInterval(id);
          qc.invalidateQueries({ queryKey: ["remix-jobs", updated.remix_project_id] });
        }
      } catch {
        clearInterval(id);
      }
    }, 2000);
    return () => clearInterval(id);
  }, [job.id, isActive, isStale, qc]);

  const stopMutation = useMutation({
    mutationFn: () => mockStopRemixJob(job.id),
    onSuccess: (updated) => {
      setJob(updated);
      qc.invalidateQueries({ queryKey: ["remix-jobs", updated.remix_project_id] });
    },
  });

  return (
    <div className="remix-job">
      <div className="flex items-center justify-between">
        <StatusBadge status={isStale ? "failed" : job.status} />
        <div className="flex items-center gap-2">
          {isActive && !isStale && (
            <button
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border border-error-bg text-error text-[0.7rem] font-semibold hover:bg-error-bg transition-colors disabled:opacity-50"
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
              type="button"
            >
              <StopIcon />
              {stopMutation.isPending ? "Stopping..." : "Stop"}
            </button>
          )}
          <span className="text-xs font-semibold text-muted">
            {job.completed_videos}/{job.total_videos} videos
          </span>
        </div>
      </div>
      {isActive && !isStale && (
        <RemixProgressBar value={job.completed_videos} max={job.total_videos} />
      )}
      {isStale && (
        <p className="text-xs text-warning">
          Job stalled -- worker may not have been running. Click Generate Videos to retry.
        </p>
      )}
      {job.status === "completed" && (
        <p className="text-xs text-success">
          {job.completed_videos} video{job.completed_videos !== 1 ? "s" : ""} created
          {job.failed_videos > 0 ? `, ${job.failed_videos} failed` : ""}
          <span className="text-muted"> · Output saved to Video Library</span>
        </p>
      )}
      {job.status === "cancelled" && (
        <p className="text-xs text-warning">
          Job cancelled · {job.completed_videos} video{job.completed_videos !== 1 ? "s" : ""} completed before stopping.
        </p>
      )}
      {job.status === "failed" && !isStale && (
        <p className="text-xs text-error">Job failed -- check clip settings and try again.</p>
      )}
      <p className="text-[0.7rem] text-muted">{new Date(job.created_at).toLocaleString()}</p>
    </div>
  );
}

/* ─── Project Detail Panel ────────────────────────────────────────────────── */
function ProjectDetailPanel({
  project,
  vLibProjects,
  onClose,
}: {
  project: RemixProject;
  vLibProjects: VideoLibraryProject[];
  onClose: () => void;
}) {
  const qc = useQueryClient();

  const analysisQuery = useQuery({
    queryKey: ["remix-analyze", project.id],
    queryFn: () => mockAnalyzeRemixProject(project.id),
  });

  const jobsQuery = useQuery({
    queryKey: ["remix-jobs", project.id],
    queryFn: () => mockListRemixJobs(project.id),
  });

  const runMutation = useMutation({
    mutationFn: () => mockCreateRemixJob(project.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["remix-jobs", project.id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => mockDeleteRemixProject(project.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["remix-projects"] });
      onClose();
    },
  });

  const analysis = analysisQuery.data;
  const jobs = jobsQuery.data ?? [];
  const hasActiveJob = jobs.some((j) => {
    const active = j.status === "running" || j.status === "pending";
    const stale = active && Date.now() - new Date(j.created_at).getTime() > STALE_PENDING_MS && j.completed_videos === 0;
    return active && !stale;
  });

  const fx = project.visual_effects as Record<string, unknown>;
  const fxParts = [
    fx.color_filter && fx.color_filter !== "none" ? String(fx.color_filter) : null,
    Number(fx.brightness) !== 0 ? `brightness ${fx.brightness}` : null,
    Number(fx.contrast) !== 0 ? `contrast ${fx.contrast}` : null,
    Number(fx.saturation) !== 0 ? `saturation ${fx.saturation}` : null,
  ].filter(Boolean);
  const fxSummary = fxParts.length > 0 ? fxParts.join(", ") : "None";

  const sourceName = project.source_project_id
    ? (vLibProjects.find((p) => p.id === project.source_project_id)?.name ?? "Unknown project")
    : "No Project (unassigned)";

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-heading text-base font-bold text-primary leading-tight">{project.name}</h2>
          <p className="text-xs text-secondary mt-0.5">
            {formatDuration(project.target_duration_ms)} · {project.clip_mode} mode
          </p>
        </div>
        <button
          onClick={onClose}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border-subtle bg-glass text-primary transition hover:border-border-active hover:bg-glass-hover shrink-0"
          aria-label="Close"
          type="button"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
        </button>
      </div>

      {/* Configuration */}
      <SectionCard title="Configuration">
        <div className="inspector-list">
          <div>
            <span>Source</span>
            <strong>{sourceName}</strong>
          </div>
          <div>
            <span>Duration</span>
            <strong>{formatDuration(project.target_duration_ms)}</strong>
          </div>
          <div>
            <span>Mode</span>
            <strong className="capitalize">{project.clip_mode}</strong>
          </div>
          <div>
            <span>Effects</span>
            <strong className="capitalize">{fxSummary}</strong>
          </div>
        </div>
      </SectionCard>

      {/* Analysis */}
      <SectionCard title="Analysis">
        {analysisQuery.isLoading ? (
          <div className="flex items-center gap-3 py-2">
            <div className="w-4 h-4 border-2 border-border-subtle border-t-accent rounded-full animate-spin shrink-0" />
            <span className="text-xs text-secondary">Analysing clips...</span>
          </div>
        ) : analysisQuery.isError ? (
          <p className="text-xs text-error">Failed to analyse.</p>
        ) : analysis ? (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="remix-stat">
                <span className="remix-stat__value text-primary-fg">{analysis.possible_videos}</span>
                <span className="remix-stat__label">Videos possible</span>
              </div>
              <div className="remix-stat">
                <span className="remix-stat__value">{analysis.total_clips}</span>
                <span className="remix-stat__label">Source clips</span>
              </div>
            </div>
            <p className="text-xs text-muted">
              {analysis.clips_with_duration} clips with duration · {formatDuration(analysis.total_duration_ms)} total footage
            </p>
            {analysis.possible_videos === 0 && (
              <p className="text-xs text-warning">
                Not enough clips/footage. Try a shorter target duration or add more clips.
              </p>
            )}
          </div>
        ) : null}
      </SectionCard>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          className="btn-primary flex-1"
          onClick={() => runMutation.mutate()}
          disabled={
            runMutation.isPending ||
            hasActiveJob ||
            !analysis ||
            analysis.possible_videos === 0
          }
          type="button"
        >
          <PlayIcon />
          {runMutation.isPending
            ? "Starting..."
            : hasActiveJob
              ? "Job running..."
              : "Generate videos"}
        </button>
        <button
          className="btn-ghost"
          style={{ color: "var(--error-fg)" }}
          onClick={() => {
            if (confirm(`Delete "${project.name}"? This cannot be undone.`)) {
              deleteMutation.mutate();
            }
          }}
          disabled={deleteMutation.isPending}
          type="button"
          title="Delete project"
        >
          <TrashIcon />
        </button>
      </div>

      {/* Jobs */}
      {jobs.length > 0 && (
        <SectionCard title={`Job history (${jobs.length})`}>
          <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
            {jobs.map((job) => (
              <JobRow key={job.id} initialJob={job} />
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

/* ─── Project Card ────────────────────────────────────────────────────────── */
function ProjectCard({
  project,
  isSelected,
  onSelect,
}: {
  project: RemixProject;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const fx = project.visual_effects as Record<string, unknown>;
  const hasEffects =
    (fx.color_filter && fx.color_filter !== "none") ||
    Number(fx.brightness) !== 0 ||
    Number(fx.contrast) !== 0 ||
    Number(fx.saturation) !== 0;

  return (
    <button
      className={`remix-card ${isSelected ? "remix-card--selected" : ""}`}
      onClick={onSelect}
      type="button"
    >
      <div className="remix-card__icon">
        <RemixIcon size={18} />
      </div>
      <p className="font-heading font-bold text-sm text-primary truncate">{project.name}</p>
      <div className="flex flex-wrap gap-1.5">
        <span className="tag-chip">{formatDuration(project.target_duration_ms)}</span>
        <span className="tag-chip capitalize">{project.clip_mode}</span>
        {hasEffects && (
          <span className="inline-flex items-center rounded-full border border-border-active bg-primary-bg px-2.5 py-1 text-xs font-medium text-primary-fg">FX</span>
        )}
      </div>
    </button>
  );
}

/* ─── Page ───────────────────────────────────────────────────────────────── */
export default function RemixPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["remix-projects"],
    queryFn: mockGetRemixProjects,
  });

  const vLibProjectsQuery = useQuery({
    queryKey: ["video-library-projects"],
    queryFn: mockGetVideoLibraryProjects,
  });

  const projects = projectsQuery.data ?? [];
  const vLibProjects = vLibProjectsQuery.data ?? [];
  const selectedProject = projects.find((p) => p.id === selectedProjectId) ?? null;

  function handleCreated(project: RemixProject) {
    qc.invalidateQueries({ queryKey: ["remix-projects"] });
    setShowCreate(false);
    setSelectedProjectId(project.id);
  }

  if (projectsQuery.isLoading) return <LoadingPage />;

  return (
    <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
      {/* Header */}
      <div className="flex items-end justify-between gap-6">
        <div className="flex flex-col gap-1.5">
          <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Bulk generation</p>
          <h1 className="font-heading text-3xl md:text-[2.5rem] leading-[1.1] font-bold text-primary tracking-tight">Remix</h1>
          <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch] mt-1">
            Bulk-generate videos by mixing and remixing your uploaded clips. Create dozens of unique videos automatically.
          </p>
        </div>
        <button
          className="btn-primary shrink-0"
          onClick={() => setShowCreate(true)}
          type="button"
        >
          <PlusIcon />
          New project
        </button>
      </div>

      {/* Body: projects grid + detail panel */}
      <div className="flex gap-6 items-start min-h-[60vh]">
        {/* Projects grid */}
        <div className="flex-1 min-w-0">
          {projects.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center gap-6 py-16 px-8 rounded-2xl bg-card border-2 border-dashed border-border-card">
              <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary-bg text-primary-fg">
                <RemixIcon />
              </div>
              <div className="flex flex-col gap-2 max-w-md">
                <h3 className="font-heading text-xl font-bold text-primary">No remix projects yet</h3>
                <p className="text-[0.9rem] leading-relaxed text-secondary">
                  Create a project to bulk-generate videos from your uploaded clips.
                </p>
              </div>
              <div className="flex flex-col gap-2 text-left max-w-sm w-full">
                {[
                  { label: "Choose source clips", detail: "Select from your Video Library projects" },
                  { label: "Configure effects", detail: "Color filters, brightness, fades, and more" },
                  { label: "Bulk generate", detail: "Automatically create dozens of unique videos" },
                ].map((item) => (
                  <div key={item.label} className="flex items-start gap-3 rounded-xl bg-glass px-3.5 py-2.5">
                    <span className="mt-1.5 h-2 w-2 rounded-full bg-accent shrink-0" />
                    <div className="flex flex-col">
                      <strong className="text-sm font-semibold text-primary">{item.label}</strong>
                      <span className="text-xs text-secondary">{item.detail}</span>
                    </div>
                  </div>
                ))}
              </div>
              <button
                className="btn-primary mt-2"
                onClick={() => setShowCreate(true)}
                type="button"
              >
                <PlusIcon />
                Create remix project
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {projects.map((p) => (
                <ProjectCard
                  key={p.id}
                  project={p}
                  isSelected={p.id === selectedProjectId}
                  onSelect={() =>
                    setSelectedProjectId(p.id === selectedProjectId ? null : p.id)
                  }
                />
              ))}
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedProject && (
          <div className="shrink-0" style={{ width: "22rem" }}>
            <div className="remix-detail">
              <ProjectDetailPanel
                project={selectedProject}
                vLibProjects={vLibProjects}
                onClose={() => setSelectedProjectId(null)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Create wizard */}
      <CreateWizardDialog
        open={showCreate}
        videoLibraryProjects={vLibProjects}
        onClose={() => setShowCreate(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}
