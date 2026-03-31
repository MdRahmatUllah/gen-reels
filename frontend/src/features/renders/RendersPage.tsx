import {
  PageFrame,
  SectionCard,
  StatusBadge,
  ProgressBar,
  MetricCard,
  EmptyState,
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

function RenderSummaryCard({ render }: { render: RenderJob }) {
  return (
    <SectionCard
      className="surface-card--hero"
      title={render.label}
      subtitle={`Consistency snapshot ${render.consistencyPackSnapshotId}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={render.status} />
        <span>{render.transitionMode === "crossfade" ? "Crossfade" : "Hard cut"}</span>
        <span>{render.musicTrack}</span>
      </div>
      <ProgressBar
        value={render.progress}
        label="Pipeline progress"
        detail={render.sseState}
      />
      <div className="metric-row">
        <MetricCard label="Voice continuity" value={render.voicePreset} detail="Frozen at render creation" tone="primary" />
        <MetricCard label="Duration" value={formatDuration(render.durationSec)} detail="Master export target" tone="neutral" />
      </div>
    </SectionCard>
  );
}

function RenderStepTable({
  projectId,
  steps,
  onRetry,
}: {
  projectId: string;
  steps: RenderStep[];
  onRetry: (id: string) => void;
}) {
  const approveFramePair = useApproveFramePair(projectId);
  const regenerateFramePair = useRegenerateFramePair(projectId);
  const hitlBusy = approveFramePair.isPending || regenerateFramePair.isPending;

  return (
    <div className="table-shell">
      <table className="studio-table">
        <thead>
          <tr>
            <th>Artifact ID</th>
            <th>Step</th>
            <th>Status</th>
            <th>Delta</th>
            <th>Cost</th>
            <th>Clip</th>
            <th>Narration</th>
            <th>Next action</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step) => (
            <tr key={step.id}>
              <td>{step.sceneId}</td>
              <td>{step.name}</td>
              <td>
                <StatusBadge status={step.status as any} />
              </td>
              <td>{formatSignedSeconds(step.durationDeltaSec)}</td>
              <td className="text-secondary">
                {step.status === "completed" ? `${step.creditCost || 5} cr` : "--"}
              </td>
              <td>{step.clipStatus}</td>
              <td>{step.narrationStatus}</td>
              <td>
                {step.stepKind === "frame_pair_generation" && step.backendStatus === "review" ? (
                  <div className="flex flex-wrap gap-1">
                    <button
                      type="button"
                      className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-glass px-2 py-1 text-[11px] font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover"
                      disabled={hitlBusy}
                      onClick={() => approveFramePair.mutate(step.id)}
                    >
                      Approve frames
                    </button>
                    <button
                      type="button"
                      className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-glass px-2 py-1 text-[11px] font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover"
                      disabled={hitlBusy}
                      onClick={() => regenerateFramePair.mutate(step.id)}
                    >
                      Regenerate
                    </button>
                  </div>
                ) : step.status === "failed" ? (
                  <button
                    className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-glass px-3 py-1.5 text-xs font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover"
                    onClick={() => onRetry(step.id)}
                  >
                    Retry
                  </button>
                ) : step.status === "blocked" ? (
                  <span className="text-[11px] font-medium text-warning">
                    Admin review required
                  </span>
                ) : (
                  step.nextAction
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

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

  // Combined render source (prefer live renders hook if populated, otherwise empty)
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
    if (!activeRender) return "Generate Video →";
    if (isRunningOrQueued) return "Rendering...";
    if (activeRender.status === "completed") return "Generate Again →";
    if (activeRender.status === "failed") return "Retry Render →";
    return "Generate Video →";
  }

  return (
    <PageFrame
      eyebrow="Render monitor"
      title={`${project.title} renders`}
      description="Build your final video — each scene's keyframes are animated with Ken Burns motion, crossfaded together, and mixed with voiceover and captions."
      actions={
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div className="flex flex-wrap items-center gap-2">
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
            <button
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
              onClick={() => cancelRender()}
              type="button"
            >
              Cancel
            </button>
          )}
          <button
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            onClick={() => setShowSettingsModal(true)}
            disabled={isStarting || isRunningOrQueued}
            type="button"
          >
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
                  <span>SSE state</span>
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
            <EmptyState title="No active job" description="Start a render to see metrics." />
          </div>
        )
      }
    >
      {activeRender ? (
        <>
          <RenderSummaryCard render={activeRender} />

          {activeRender.status === "completed" && activeRender.exportUrl && (
            <SectionCard title="Export preview">
              <video
                controls
                playsInline
                src={activeRender.exportUrl}
                style={{ width: "100%", maxWidth: "360px", borderRadius: "12px", display: "block" }}
              />
              <div className="flex flex-wrap items-center gap-3 mt-3">
                <a
                  href={activeRender.exportUrl}
                  download="export.mp4"
                  className="inline-flex items-center gap-2 rounded-xl bg-accent-gradient px-4 py-2 text-sm font-semibold text-on-accent shadow-sm hover:shadow-accent"
                >
                  Download MP4
                </a>
                <Link
                  to={`/app/projects/${project.id}/exports`}
                  className="inline-flex items-center gap-2 rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary hover:border-border-active hover:bg-glass-hover"
                >
                  Open exports →
                </Link>
              </div>
            </SectionCard>
          )}

          <div className="content-grid content-grid--equal">
            <SectionCard title="Composition gate" subtitle="Mirrors the checks defined in the composition and A/V consistency architecture">
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

            <SectionCard title="Event stream" subtitle="A mock view of live render activity surfaced through SSE">
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

          <SectionCard title="Per-scene execution matrix" subtitle="Retry decisions can stay scoped to the smallest broken unit">
            {activeRender.steps.length > 0 ? (
              <RenderStepTable
                projectId={project.id}
                steps={activeRender.steps}
                onRetry={(id) => retryStep(id)}
              />
            ) : (
              <EmptyState
                title="No active scene steps"
                description="This render already completed, so only the archived metrics remain."
              />
            )}
          </SectionCard>
        </>
      ) : (
        <EmptyState
          title="Ready to Render"
          description="You have approved your Scene Plan. Generate a render to start the FFmpeg + AI composition pipeline."
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
