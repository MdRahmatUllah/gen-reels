import {
  PageFrame,
  SectionCard,
  StatusBadge,
  ProgressBar,
  LoadingPage,
} from "../../components/ui";
import { Link, useParams } from "react-router-dom";
import { useProject } from "../../hooks/use-projects";
import { useStudioUiStore } from "../../state/ui-store";
import {
  useRenders,
  useStartRender,
  useCancelRender,
  useRetryRenderStep,
  useApproveFramePair,
  useRegenerateFramePair,
} from "../../hooks/use-renders";
import type { RenderJob, RenderStep } from "../../types/domain";
import { RenderSettingsModal } from "./RenderSettingsModal";
import { useState } from "react";

/* ─── Icons ───────────────────────────────────────────────────────────────── */
function PlayIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

function ArrowRightIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function DownloadIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  );
}

function XIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function RefreshIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M23 4v6h-6M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
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

function FilmIcon({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polygon points="23 7 16 12 23 17 23 7" />
      <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
    </svg>
  );
}

function EyeIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function MicIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3zM19 10v2a7 7 0 01-14 0v-2" />
    </svg>
  );
}

/* ─── Helpers ─────────────────────────────────────────────────────────────── */
function formatDuration(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s < 10 ? "0" : ""}${s}s`;
}

function formatSignedSeconds(sec: number) {
  if (sec === 0) return "--";
  const sign = sec > 0 ? "+" : "";
  return `${sign}${sec.toFixed(1)}s`;
}

/* ─── Progress Ring ───────────────────────────────────────────────────────── */
function ProgressRing({ progress, size = 64 }: { progress: number; size?: number }) {
  const stroke = 5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;
  const color =
    progress >= 100
      ? "var(--success-fg)"
      : progress >= 50
        ? "var(--accent)"
        : "var(--warning-fg)";

  return (
    <div className="render-progress-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border-subtle)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <span className="absolute text-[0.85rem] font-bold text-primary font-heading">{progress}%</span>
    </div>
  );
}

/* ─── Render Summary Card ─────────────────────────────────────────────────── */
function RenderSummaryCard({ render }: { render: RenderJob }) {
  return (
    <SectionCard
      className="surface-card--hero"
      title={render.label}
      subtitle={`Snapshot ${render.consistencyPackSnapshotId}`}
    >
      <div className="flex items-start gap-5">
        <ProgressRing progress={render.progress} />
        <div className="flex-1 min-w-0 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={render.status} />
            <span className="tag-chip">{render.transitionMode === "crossfade" ? "Crossfade" : "Hard cut"}</span>
            <span className="tag-chip">{render.musicTrack}</span>
          </div>
          <ProgressBar
            value={render.progress}
            label="Pipeline progress"
            detail={render.sseState}
          />
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-3 mt-2">
        {[
          { label: "Voice", value: render.voicePreset, bg: "bg-primary-bg", fg: "text-primary-fg" },
          { label: "Duration", value: formatDuration(render.durationSec), bg: "bg-[rgba(14,165,233,0.12)]", fg: "text-accent-secondary" },
          { label: "Status", value: render.sseState, bg: render.status === "completed" ? "bg-success-bg" : "bg-warning-bg", fg: render.status === "completed" ? "text-success" : "text-warning" },
        ].map((stat) => (
          <div key={stat.label} className="stat-card animate-rise-in">
            <div className={`stat-card__icon ${stat.bg} ${stat.fg}`}>
              {stat.label === "Voice" ? <MicIcon size={16} /> : stat.label === "Duration" ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
              ) : <PlayIcon size={16} />}
            </div>
            <div className="flex flex-col">
              <span className="stat-card__value text-base">{stat.value}</span>
              <span className="stat-card__label">{stat.label}</span>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

/* ─── Render Step Card ────────────────────────────────────────────────────── */
function RenderStepCard({
  step,
  index,
  projectId,
  onRetry,
}: {
  step: RenderStep;
  index: number;
  projectId: string;
  onRetry: (id: string) => void;
}) {
  const approveFramePair = useApproveFramePair(projectId);
  const regenerateFramePair = useRegenerateFramePair(projectId);
  const hitlBusy = approveFramePair.isPending || regenerateFramePair.isPending;

  const needsReview = step.stepKind === "frame_pair_generation" && step.backendStatus === "review";

  return (
    <div className="render-step" style={{ animationDelay: `${index * 50}ms` }}>
      <span className="render-step__number">{index + 1}</span>
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <span className="text-[0.6875rem] tracking-widest uppercase font-bold text-muted">{step.sceneId}</span>
            <strong className="font-heading text-[0.95rem] font-bold text-primary leading-snug">{step.name}</strong>
          </div>
          <div className="flex items-center gap-2">
            {step.status === "completed" && (
              <span className="text-[0.7rem] font-semibold text-muted">{step.creditCost || 5} cr</span>
            )}
            <StatusBadge status={step.status as string} />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 pt-1">
          <span className="render-step__meta">
            <EyeIcon /> Clip: {step.clipStatus}
          </span>
          <span className="render-step__meta">
            <MicIcon /> Narration: {step.narrationStatus}
          </span>
          {step.durationDeltaSec !== 0 && (
            <span className={`render-step__meta ${step.durationDeltaSec > 0 ? "text-warning" : "text-success"}`}>
              Delta: {formatSignedSeconds(step.durationDeltaSec)}
            </span>
          )}
        </div>

        {/* Action row */}
        {(needsReview || step.status === "failed" || step.status === "blocked") && (
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border-subtle">
            {needsReview ? (
              <>
                <button
                  type="button"
                  className="btn-primary"
                  style={{ minHeight: "2rem", padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
                  disabled={hitlBusy}
                  onClick={() => approveFramePair.mutate(step.id)}
                >
                  <CheckIcon size={13} />
                  Approve frames
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  style={{ minHeight: "2rem", padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
                  disabled={hitlBusy}
                  onClick={() => regenerateFramePair.mutate(step.id)}
                >
                  <RefreshIcon size={13} />
                  Regenerate
                </button>
              </>
            ) : step.status === "failed" ? (
              <button
                type="button"
                className="btn-ghost"
                style={{ minHeight: "2rem", padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
                onClick={() => onRetry(step.id)}
              >
                <RefreshIcon size={13} />
                Retry step
              </button>
            ) : step.status === "blocked" ? (
              <span className="text-[0.78rem] font-semibold text-warning flex items-center gap-1.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" />
                </svg>
                Admin review required
              </span>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Render Steps List ───────────────────────────────────────────────────── */
function RenderStepsList({
  projectId,
  steps,
  onRetry,
}: {
  projectId: string;
  steps: RenderStep[];
  onRetry: (id: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {steps.map((step, index) => (
        <RenderStepCard
          key={step.id}
          step={step}
          index={index}
          projectId={projectId}
          onRetry={onRetry}
        />
      ))}
    </div>
  );
}

/* ─── Empty Render State ──────────────────────────────────────────────────── */
function EmptyRenderState({ onGenerate, disabled }: { onGenerate: () => void; disabled: boolean }) {
  return (
    <div className="render-empty">
      <div className="render-empty__icon">
        <FilmIcon />
      </div>
      <div className="flex flex-col gap-2 max-w-md">
        <h3 className="font-heading text-xl font-bold text-primary">Ready to render</h3>
        <p className="text-[0.9rem] leading-relaxed text-secondary">
          Your scene plan is approved. Generate a render to start the composition pipeline -- keyframes are animated, crossfaded, and mixed with voiceover and music.
        </p>
      </div>
      <div className="flex flex-col gap-2 text-left max-w-sm w-full">
        {[
          { label: "Keyframe animation", detail: "Ken Burns motion applied to each scene" },
          { label: "Audio mixing", detail: "Voiceover, music, and ducking composed" },
          { label: "Final composition", detail: "Scenes crossfaded into the master export" },
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
      <button className="btn-primary mt-2" onClick={onGenerate} disabled={disabled} type="button">
        <PlayIcon />
        Generate video
      </button>
    </div>
  );
}

/* ─── Renders Page ────────────────────────────────────────────────────────── */
export function RendersPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading: projectLoading } = useProject(projectId || "");
  const renderFilter = useStudioUiStore((state: any) => state.renderFilter);
  const setRenderFilter = useStudioUiStore((state: any) => state.setRenderFilter);

  const { data: renders } = useRenders(project?.id || "");
  const { mutate: startRender, isPending: isStarting } = useStartRender(project?.id || "");
  const { mutate: cancelRender } = useCancelRender(project?.id || "");
  const { mutate: retryStep } = useRetryRenderStep(project?.id || "");

  const [showSettingsModal, setShowSettingsModal] = useState(false);

  if (projectLoading || !project) {
    return <LoadingPage />;
  }

  const allRenders = renders || [];
  const filteredRenders = allRenders.filter((render) => {
    if (renderFilter === "all") return true;
    if (renderFilter === "completed") return render.status === "completed";
    return render.status === renderFilter;
  });

  const activeRender = filteredRenders[0] ?? allRenders[0];
  const isRunningOrQueued = activeRender?.status === "running" || activeRender?.status === "queued";

  function generateButtonLabel() {
    if (isStarting) return "Starting...";
    if (!activeRender) return "Generate video";
    if (isRunningOrQueued) return "Rendering...";
    if (activeRender.status === "completed") return "Render again";
    if (activeRender.status === "failed") return "Retry render";
    return "Generate video";
  }

  return (
    <PageFrame
      eyebrow="Render monitor"
      title={`${project.title} renders`}
      description="Build your final video -- keyframes are animated, crossfaded, and mixed with voiceover, captions, and music."
      actions={
        <div className="flex items-center gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {(["all", "running", "blocked", "completed"] as const).map((filter) => (
              <button
                key={filter}
                className={renderFilter === filter ? "chip-button chip-button--active" : "chip-button"}
                onClick={() => setRenderFilter(filter)}
                type="button"
              >
                {filter}
              </button>
            ))}
          </div>
          {isRunningOrQueued && (
            <button className="btn-ghost" onClick={() => cancelRender()} type="button">
              <XIcon size={14} />
              Cancel
            </button>
          )}
          <button
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={() => setShowSettingsModal(true)}
            disabled={isStarting || isRunningOrQueued}
            type="button"
          >
            <PlayIcon />
            {generateButtonLabel()}
          </button>
        </div>
      }
      inspector={
        activeRender ? (
          <div className="inspector-stack">
            <SectionCard title="Render facts">
              <div className="inspector-list">
                <div>
                  <span>Pipeline state</span>
                  <strong>{activeRender.sseState}</strong>
                </div>
                <div>
                  <span>Voice preset</span>
                  <strong>{activeRender.voicePreset}</strong>
                </div>
                <div>
                  <span>Music fallback</span>
                  <strong>{activeRender.allowExportWithoutMusic ? "Allowed" : "Required"}</strong>
                </div>
                <div>
                  <span>Next action</span>
                  <strong>{activeRender.nextAction}</strong>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Mix targets">
              <div className="inspector-list">
                <div>
                  <span>Loudness</span>
                  <strong>{activeRender.metrics.lufsTarget}</strong>
                </div>
                <div>
                  <span>Peak ceiling</span>
                  <strong>{activeRender.metrics.truePeak}</strong>
                </div>
                <div>
                  <span>Music ducking</span>
                  <strong>{activeRender.metrics.musicDucking}</strong>
                </div>
                <div>
                  <span>Subtitles</span>
                  <strong>{activeRender.metrics.subtitleState}</strong>
                </div>
              </div>
            </SectionCard>
          </div>
        ) : (
          <div className="inspector-stack">
            <SectionCard title="No active job">
              <div className="flex flex-col items-center gap-2.5 py-3 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-glass text-muted">
                  <PlayIcon size={18} />
                </div>
                <p className="text-xs text-secondary leading-relaxed max-w-[14rem]">
                  Start a render to see pipeline metrics and progress
                </p>
              </div>
            </SectionCard>
          </div>
        )
      }
    >
      {activeRender ? (
        <>
          <RenderSummaryCard render={activeRender} />

          {/* Export preview */}
          {activeRender.status === "completed" && activeRender.exportUrl && (
            <SectionCard title="Export preview" subtitle="Your rendered video is ready for download">
              <div className="flex flex-col sm:flex-row gap-5 items-start">
                <video
                  controls
                  playsInline
                  src={activeRender.exportUrl}
                  className="w-full sm:max-w-[360px] rounded-xl border border-border-card shadow-card"
                />
                <div className="flex flex-col gap-3">
                  <a
                    href={activeRender.exportUrl}
                    download="export.mp4"
                    className="btn-primary"
                  >
                    <DownloadIcon />
                    Download MP4
                  </a>
                  <Link
                    to={`/app/projects/${project.id}/exports`}
                    className="btn-ghost"
                  >
                    Open exports
                    <ArrowRightIcon />
                  </Link>
                </div>
              </div>
            </SectionCard>
          )}

          {/* Composition checks + event stream */}
          <div className="content-grid content-grid--equal">
            <SectionCard title="Composition gate" subtitle="Quality checks for the final render">
              <div className="check-list">
                {activeRender.checks.map((check) => (
                  <div className="check-item" key={check.id}>
                    <StatusBadge status={check.status} />
                    <div>
                      <strong>{check.label}</strong>
                      <p>{check.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Event stream" subtitle="Live render activity log">
              <div className="event-stream">
                {activeRender.events.map((event) => (
                  <div className="event-item" key={event.id}>
                    <span className={`tone-pill tone-pill--${event.tone}`} />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <strong>{event.label}</strong>
                        <span>{event.time}</span>
                      </div>
                      <p>{event.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

          {/* Per-scene execution */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-col gap-0.5">
                <h3 className="font-heading text-[1.05rem] font-bold text-primary">Scene execution</h3>
                <p className="text-[0.85rem] text-secondary">
                  {activeRender.steps.length} steps across the render pipeline
                </p>
              </div>
              {activeRender.steps.length > 0 && (
                <span className="text-[0.7rem] font-bold text-muted px-3 py-1.5 rounded-full bg-glass border border-border-subtle uppercase tracking-wider whitespace-nowrap">
                  {activeRender.steps.filter((s) => s.status === "completed").length} / {activeRender.steps.length} done
                </span>
              )}
            </div>
            {activeRender.steps.length > 0 ? (
              <RenderStepsList
                projectId={project.id}
                steps={activeRender.steps}
                onRetry={(id) => retryStep(id)}
              />
            ) : (
              <div className="flex flex-col items-center gap-2.5 py-8 text-center rounded-2xl bg-card border border-border-card">
                <p className="text-sm text-secondary">No active scene steps -- only archived metrics remain</p>
              </div>
            )}
          </div>
        </>
      ) : (
        <EmptyRenderState
          onGenerate={() => setShowSettingsModal(true)}
          disabled={isStarting || isRunningOrQueued}
        />
      )}

      {showSettingsModal && (
        <RenderSettingsModal
          onClose={() => setShowSettingsModal(false)}
          onConfirm={(settings) => {
            startRender(settings);
            setShowSettingsModal(false);
          }}
          isStarting={isStarting}
        />
      )}
    </PageFrame>
  );
}
