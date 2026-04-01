import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dialog } from "../../components/Dialog";
import { EmptyState, LoadingPage, PageFrame, SectionCard } from "../../components/ui";
import {
  mockGetRemixProjects,
  mockCreateRemixProject,
  mockDeleteRemixProject,
  mockAnalyzeRemixProject,
  mockCreateRemixJob,
  mockGetRemixJob,
  mockListRemixJobs,
  mockGetVideoLibraryProjects,
} from "../../lib/mock-service";
import type {
  RemixProject,
  RemixAnalysis,
  RemixJob,
  VideoLibraryProject,
} from "../../types/domain";

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

/* ─── Status badge ────────────────────────────────────────────────────────── */
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-zinc-700 text-zinc-300",
    running: "bg-blue-900/60 text-blue-300",
    completed: "bg-emerald-900/60 text-emerald-300",
    failed: "bg-red-900/60 text-red-300",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${map[status] ?? map.pending}`}>
      {status}
    </span>
  );
}

/* ─── Progress bar ────────────────────────────────────────────────────────── */
function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="w-full bg-zinc-700 rounded-full h-2 overflow-hidden">
      <div
        className="h-2 rounded-full bg-indigo-500 transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/* ─── Create Wizard ──────────────────────────────────────────────────────── */
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

function CreateWizardModal({
  videoLibraryProjects,
  onClose,
  onCreated,
}: {
  videoLibraryProjects: VideoLibraryProject[];
  onClose: () => void;
  onCreated: (project: RemixProject) => void;
}) {
  const [step, setStep] = useState<WizardStep>("name");
  const [form, setForm] = useState<WizardState>(DEFAULT_WIZARD);
  const [error, setError] = useState("");

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
    if (stepIndex > 0) setStep(STEPS[stepIndex - 1]);
  }

  const stepLabel: Record<WizardStep, string> = {
    name: "Project Name",
    source: "Source Folder",
    effects: "Visual Effects",
    duration: "Target Duration",
    mode: "Clip Mode",
  };

  return (
    <Dialog title="Create Remix Project" onClose={onClose}>
      {/* Step indicator */}
      <div className="flex gap-1 mb-6">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              i <= stepIndex ? "bg-indigo-500" : "bg-zinc-700"
            }`}
          />
        ))}
      </div>

      <p className="text-xs text-zinc-400 mb-4 uppercase tracking-widest">{stepLabel[step]}</p>

      {/* ── Step: Name ── */}
      {step === "name" && (
        <div className="space-y-3">
          <input
            autoFocus
            type="text"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
            placeholder="e.g. Summer Travel Mix"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && next()}
          />
        </div>
      )}

      {/* ── Step: Source folder ── */}
      {step === "source" && (
        <div className="space-y-2">
          <button
            className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
              form.source_project_id === null
                ? "border-indigo-500 bg-indigo-950/40 text-white"
                : "border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500"
            }`}
            onClick={() => setForm({ ...form, source_project_id: null })}
          >
            <div className="font-medium">No Project</div>
            <div className="text-xs text-zinc-400 mt-0.5">Clips not assigned to any project</div>
          </button>
          {videoLibraryProjects.map((p) => (
            <button
              key={p.id}
              className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                form.source_project_id === p.id
                  ? "border-indigo-500 bg-indigo-950/40 text-white"
                  : "border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500"
              }`}
              onClick={() => setForm({ ...form, source_project_id: p.id })}
            >
              <div className="font-medium">{p.name}</div>
              {p.description && <div className="text-xs text-zinc-400 mt-0.5">{p.description}</div>}
            </button>
          ))}
          {videoLibraryProjects.length === 0 && (
            <p className="text-sm text-zinc-500 text-center py-4">No projects in Video Library yet.</p>
          )}
        </div>
      )}

      {/* ── Step: Effects ── */}
      {step === "effects" && (
        <div className="space-y-4">
          <div>
            <label className="text-xs text-zinc-400 mb-1.5 block">Color Filter</label>
            <div className="grid grid-cols-4 gap-2">
              {EFFECT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={`py-2 rounded-lg text-xs font-medium border transition-colors ${
                    form.color_filter === opt.value
                      ? "border-indigo-500 bg-indigo-950/50 text-indigo-300"
                      : "border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-500"
                  }`}
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
              <div key={key}>
                <label className="text-xs text-zinc-400 mb-1 block">
                  {label} <span className="text-zinc-300">{form[key] as number}</span>
                </label>
                <input
                  type="range"
                  min={min}
                  max={max}
                  value={form[key] as number}
                  onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
                  className="w-full accent-indigo-500"
                />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">
                Fade In <span className="text-zinc-300">{form.fade_in_sec}s</span>
              </label>
              <input
                type="range" min={0} max={3} step={0.5}
                value={form.fade_in_sec}
                onChange={(e) => setForm({ ...form, fade_in_sec: Number(e.target.value) })}
                className="w-full accent-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">
                Fade Out <span className="text-zinc-300">{form.fade_out_sec}s</span>
              </label>
              <input
                type="range" min={0} max={3} step={0.5}
                value={form.fade_out_sec}
                onChange={(e) => setForm({ ...form, fade_out_sec: Number(e.target.value) })}
                className="w-full accent-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">
                Vignette <span className="text-zinc-300">{form.vignette_strength}</span>
              </label>
              <input
                type="range" min={0} max={100} step={5}
                value={form.vignette_strength}
                onChange={(e) => setForm({ ...form, vignette_strength: Number(e.target.value) })}
                className="w-full accent-indigo-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Step: Duration ── */}
      {step === "duration" && (
        <div className="space-y-4">
          <div className="grid grid-cols-5 gap-2">
            {DURATION_PRESETS.map((p) => (
              <button
                key={p.ms}
                className={`py-3 rounded-lg text-sm font-semibold border transition-colors ${
                  form.target_duration_ms === p.ms
                    ? "border-indigo-500 bg-indigo-950/50 text-indigo-300"
                    : "border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-500"
                }`}
                onClick={() => setForm({ ...form, target_duration_ms: p.ms })}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1.5 block">
              Custom duration (seconds)
            </label>
            <input
              type="number"
              min={5}
              max={600}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
              value={Math.round(form.target_duration_ms / 1000)}
              onChange={(e) => {
                const secs = Math.max(5, Math.min(600, Number(e.target.value)));
                setForm({ ...form, target_duration_ms: secs * 1000 });
              }}
            />
          </div>
          <p className="text-xs text-zinc-500">
            Videos may be slightly shorter or longer depending on clip lengths.
          </p>
        </div>
      )}

      {/* ── Step: Mode ── */}
      {step === "mode" && (
        <div className="space-y-3">
          <button
            className={`w-full text-left px-4 py-4 rounded-lg border transition-colors ${
              form.clip_mode === "random"
                ? "border-indigo-500 bg-indigo-950/40"
                : "border-zinc-700 bg-zinc-800/50 hover:border-zinc-500"
            }`}
            onClick={() => setForm({ ...form, clip_mode: "random" })}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-white text-sm">Random Clip</span>
              {form.clip_mode === "random" && (
                <span className="text-indigo-400 text-xs font-semibold">Selected</span>
              )}
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              Clips can be reused across videos. Each video starts with a unique first clip.
              Maximises volume — one video per source clip.
            </p>
          </button>
          <button
            className={`w-full text-left px-4 py-4 rounded-lg border transition-colors ${
              form.clip_mode === "unique"
                ? "border-indigo-500 bg-indigo-950/40"
                : "border-zinc-700 bg-zinc-800/50 hover:border-zinc-500"
            }`}
            onClick={() => setForm({ ...form, clip_mode: "unique" })}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-white text-sm">Unique Clip</span>
              {form.clip_mode === "unique" && (
                <span className="text-indigo-400 text-xs font-semibold">Selected</span>
              )}
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              No clip appears in more than one video. Every video is completely distinct.
              Video count limited by total available footage.
            </p>
          </button>
        </div>
      )}

      {error && <p className="text-xs text-red-400 mt-3">{error}</p>}

      {/* Footer */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-zinc-800">
        <button
          className="text-sm text-zinc-400 hover:text-white transition-colors disabled:opacity-40"
          onClick={back}
          disabled={stepIndex === 0}
        >
          ← Back
        </button>
        <button
          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          onClick={next}
          disabled={createMutation.isPending}
        >
          {isLast ? (createMutation.isPending ? "Creating…" : "Create Project") : "Next →"}
        </button>
      </div>
    </Dialog>
  );
}

/* ─── Analysis + Run Panel ───────────────────────────────────────────────── */
function ProjectDetailPanel({
  project,
  onClose,
  onJobStarted,
}: {
  project: RemixProject;
  onClose: () => void;
  onJobStarted: (job: RemixJob) => void;
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
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: ["remix-jobs", project.id] });
      onJobStarted(job);
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
  const activeJob = jobs.find((j) => j.status === "running" || j.status === "pending");

  const fx = project.visual_effects as Record<string, unknown>;
  const fxSummary = [
    fx.color_filter && fx.color_filter !== "none" ? String(fx.color_filter) : null,
    Number(fx.brightness) !== 0 ? `brightness ${fx.brightness}` : null,
    Number(fx.contrast) !== 0 ? `contrast ${fx.contrast}` : null,
    Number(fx.saturation) !== 0 ? `saturation ${fx.saturation}` : null,
  ]
    .filter(Boolean)
    .join(", ") || "None";

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">{project.name}</h2>
          <div className="flex items-center gap-3 mt-1 text-xs text-zinc-400">
            <span>Target: {formatDuration(project.target_duration_ms)}</span>
            <span>•</span>
            <span className="capitalize">{project.clip_mode} clips</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-zinc-500 hover:text-white text-lg leading-none"
        >
          ×
        </button>
      </div>

      {/* Config summary */}
      <SectionCard title="Configuration">
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <div className="text-zinc-400">Source folder</div>
          <div className="text-zinc-200 text-right">
            {project.source_project_id ? "Selected project" : "No Project (unassigned)"}
          </div>
          <div className="text-zinc-400">Duration</div>
          <div className="text-zinc-200 text-right">{formatDuration(project.target_duration_ms)}</div>
          <div className="text-zinc-400">Mode</div>
          <div className="text-zinc-200 text-right capitalize">{project.clip_mode}</div>
          <div className="text-zinc-400">Effects</div>
          <div className="text-zinc-200 text-right capitalize">{fxSummary}</div>
        </div>
      </SectionCard>

      {/* Analysis */}
      <SectionCard title="Analysis">
        {analysisQuery.isLoading ? (
          <p className="text-sm text-zinc-400">Analysing…</p>
        ) : analysis ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-indigo-400">{analysis.possible_videos}</div>
                <div className="text-xs text-zinc-400 mt-0.5">Videos possible</div>
              </div>
              <div className="bg-zinc-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-zinc-200">{analysis.total_clips}</div>
                <div className="text-xs text-zinc-400 mt-0.5">Source clips</div>
              </div>
            </div>
            <div className="text-xs text-zinc-500">
              {analysis.clips_with_duration} clips have duration metadata •{" "}
              {formatDuration(analysis.total_duration_ms)} total footage
            </div>
            {analysis.possible_videos === 0 && (
              <p className="text-xs text-amber-400">
                Not enough clips or footage to create videos at this duration. Try a shorter
                target or add more clips to the source folder.
              </p>
            )}
          </div>
        ) : null}
      </SectionCard>

      {/* Run */}
      <div className="flex gap-3">
        <button
          className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
          onClick={() => runMutation.mutate()}
          disabled={
            runMutation.isPending ||
            !!activeJob ||
            !analysis ||
            analysis.possible_videos === 0
          }
        >
          {runMutation.isPending ? "Starting…" : activeJob ? "Job running…" : "Generate Videos"}
        </button>
        <button
          className="px-4 py-2.5 border border-red-800 text-red-400 hover:bg-red-950/40 text-sm rounded-lg transition-colors disabled:opacity-50"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
        >
          Delete
        </button>
      </div>

      {/* Jobs history */}
      {jobs.length > 0 && (
        <SectionCard title="Job History">
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobRow key={job.id} job={job} />
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

/* ─── Job row ────────────────────────────────────────────────────────────── */
function JobRow({ job }: { job: RemixJob }) {
  const qc = useQueryClient();

  // Poll while running
  useEffect(() => {
    if (job.status !== "running" && job.status !== "pending") return;
    const id = setInterval(async () => {
      const updated = await mockGetRemixJob(job.id);
      qc.setQueryData(["remix-jobs", updated.remix_project_id], (old: RemixJob[] | undefined) =>
        old ? old.map((j) => (j.id === updated.id ? updated : j)) : [updated]
      );
      if (updated.status === "completed" || updated.status === "failed") {
        clearInterval(id);
        qc.invalidateQueries({ queryKey: ["remix-jobs", updated.remix_project_id] });
      }
    }, 2000);
    return () => clearInterval(id);
  }, [job.id, job.status, qc]);

  return (
    <div className="bg-zinc-800/60 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <StatusBadge status={job.status} />
        <span className="text-xs text-zinc-500">
          {job.completed_videos}/{job.total_videos} videos
        </span>
      </div>
      {(job.status === "running" || job.status === "pending") && (
        <ProgressBar value={job.completed_videos} max={job.total_videos} />
      )}
      {job.status === "completed" && (
        <p className="text-xs text-emerald-400">
          {job.completed_videos} videos created
          {job.failed_videos > 0 && `, ${job.failed_videos} failed`}
          {job.failed_videos > 0 && " — check Video Library for results"}
        </p>
      )}
      {job.status === "completed" && job.failed_videos === 0 && (
        <p className="text-xs text-zinc-400">
          Output saved to Video Library › <span className="text-white font-medium">same project name</span>
        </p>
      )}
    </div>
  );
}

/* ─── Project card ───────────────────────────────────────────────────────── */
function ProjectCard({
  project,
  onSelect,
}: {
  project: RemixProject;
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
      className="w-full text-left bg-zinc-900 border border-zinc-800 hover:border-zinc-600 rounded-xl p-4 transition-colors group"
      onClick={onSelect}
    >
      {/* Icon */}
      <div className="w-10 h-10 rounded-lg bg-indigo-950/60 border border-indigo-900/40 flex items-center justify-center mb-3">
        <svg className="w-5 h-5 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </div>
      <h3 className="font-semibold text-white text-sm mb-1">{project.name}</h3>
      <div className="flex flex-wrap gap-1.5 mt-2">
        <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
          {formatDuration(project.target_duration_ms)}
        </span>
        <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full capitalize">
          {project.clip_mode}
        </span>
        {hasEffects && (
          <span className="text-xs bg-zinc-800 text-indigo-400 px-2 py-0.5 rounded-full">
            FX
          </span>
        )}
      </div>
    </button>
  );
}

/* ─── Main page ──────────────────────────────────────────────────────────── */
export default function RemixPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedProject, setSelectedProject] = useState<RemixProject | null>(null);

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

  function handleCreated(project: RemixProject) {
    qc.invalidateQueries({ queryKey: ["remix-projects"] });
    setShowCreate(false);
    setSelectedProject(project);
  }

  if (projectsQuery.isLoading) return <LoadingPage />;

  return (
    <PageFrame
      title="Remix"
      actions={
        <button
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
          onClick={() => setShowCreate(true)}
        >
          + New Remix Project
        </button>
      }
    >
      <div className="flex gap-6 h-full">
        {/* Left: project list */}
        <div className="flex-1 min-w-0">
          {projects.length === 0 ? (
            <EmptyState
              title="No remix projects yet"
              description="Create a project to bulk-generate videos from your uploaded clips."
              action={
                <button
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
                  onClick={() => setShowCreate(true)}
                >
                  Create Remix Project
                </button>
              }
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {projects.map((p) => (
                <ProjectCard
                  key={p.id}
                  project={p}
                  onSelect={() => setSelectedProject(p)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: detail panel */}
        {selectedProject && (
          <div className="w-96 shrink-0 bg-zinc-900 border border-zinc-800 rounded-xl p-5 overflow-y-auto">
            <ProjectDetailPanel
              project={selectedProject}
              onClose={() => setSelectedProject(null)}
              onJobStarted={() => {
                qc.invalidateQueries({ queryKey: ["remix-jobs", selectedProject.id] });
              }}
            />
          </div>
        )}
      </div>

      {showCreate && (
        <CreateWizardModal
          videoLibraryProjects={vLibProjects}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
    </PageFrame>
  );
}
