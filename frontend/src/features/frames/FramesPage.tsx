import { useCallback, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  EmptyState,
  LoadingPage,
  PageFrame,
  SectionCard,
  StatusBadge,
} from "../../components/ui";
import { isMockMode } from "../../lib/config";
import { useProject, useQuickCreateStatus } from "../../hooks/use-projects";
import { useScenePlan } from "../../hooks/use-scenes";
import {
  useApproveFramePair,
  useGenerateNarration,
  useRegenerateFramePair,
  useRenders,
  useRetryRenderStep,
  useStartRender,
} from "../../hooks/use-renders";
import { useProviderExecutionPolicy } from "../../hooks/use-providers";
import { QuickStartStatusBanner } from "../projects/quick-start";
import type { RenderJob, RenderStep } from "../../types/domain";

const AZURE_VOICES = [
  "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse", "marin", "cedar",
] as const;

function latestRenderForPlan(renders: RenderJob[] | undefined, planId: string): RenderJob | null {
  if (!renders?.length) return null;
  const matches = renders.filter((r) => r.scenePlanId === planId);
  const pool = matches.length ? matches : renders;
  const sorted = [...pool].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  return sorted[0] ?? null;
}

function frameStepForScene(render: RenderJob, sceneSegmentId: string): RenderStep | undefined {
  return render.steps.find(
    (s) => s.stepKind === "frame_pair_generation" && s.sceneId === sceneSegmentId,
  );
}

function assetUrl(render: RenderJob, sceneSegmentId: string, role: string): string | null {
  return (
    render.frameAssets?.find((a) => a.sceneSegmentId === sceneSegmentId && a.assetRole === role)
      ?.downloadUrl ?? null
  );
}

function firstFailedStep(render: RenderJob): RenderStep | undefined {
  return render.steps.find((s) => s.backendStatus === "failed");
}

function narrationUrl(render: RenderJob, sceneSegmentId: string): string | null {
  const matches = render.frameAssets?.filter(
    (a) => a.sceneSegmentId === sceneSegmentId && a.assetRole === "narration_track",
  );
  if (!matches?.length) return null;
  return matches[matches.length - 1].downloadUrl ?? null;
}

function NarrationCard({
  audioSrc,
  sceneId,
  renderJobId,
  speechConfigured,
  generateNarration,
  isGenerating,
}: {
  audioSrc: string | null;
  sceneId: string;
  renderJobId: string;
  speechConfigured: boolean;
  generateNarration: (args: { renderJobId: string; sceneSegmentId: string; voice?: string }) => void;
  isGenerating: boolean;
}) {
  const [voice, setVoice] = useState("alloy");
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  const toggle = useCallback(() => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      el.play();
      setPlaying(true);
    }
  }, [playing]);

  if (!speechConfigured) {
    return (
      <div className="mt-3 rounded-lg border border-border-subtle bg-glass/50 px-3 py-2">
        <p className="text-xs text-muted mb-1.5">Voice narration requires an audio provider.</p>
        <Link
          to="/app/settings/providers"
          className="inline-flex items-center gap-1 rounded-md bg-accent-gradient px-2.5 py-1 text-[11px] font-semibold text-on-accent shadow-sm hover:shadow-accent"
        >
          Set up audio provider
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-lg border border-border-subtle bg-glass/50 px-3 py-2.5">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-medium text-muted uppercase tracking-wider">Voice</span>
        <select
          value={voice}
          onChange={(e) => setVoice(e.target.value)}
          className="rounded-md border border-border-subtle bg-surface px-2 py-0.5 text-xs text-primary focus:border-border-active focus:outline-none"
        >
          {AZURE_VOICES.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={isGenerating}
          onClick={() => generateNarration({ renderJobId, sceneSegmentId: sceneId, voice })}
          className="inline-flex items-center gap-1 rounded-md bg-accent-gradient px-2.5 py-1 text-[11px] font-semibold text-on-accent shadow-sm hover:shadow-accent disabled:opacity-50"
        >
          {isGenerating ? "Generating…" : audioSrc ? "Regenerate" : "Generate voice"}
        </button>
      </div>
      {audioSrc ? (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggle}
            className="flex h-7 w-7 items-center justify-center rounded-full border border-border-subtle bg-surface text-primary hover:bg-glass"
          >
            {playing ? "⏸" : "▶"}
          </button>
          <audio
            key={audioSrc}
            ref={audioRef}
            src={audioSrc}
            onEnded={() => setPlaying(false)}
            preload="metadata"
            className="hidden"
          />
          <span className="text-[11px] text-secondary">Narration ready</span>
          <a
            href={audioSrc}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto text-[11px] text-accent hover:underline"
          >
            Download
          </a>
        </div>
      ) : null}
    </div>
  );
}

function FrameLightbox({
  src,
  alt,
  onClose,
}: {
  src: string;
  alt: string;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-h-[90vh] max-w-[90vw] flex flex-col items-center gap-3"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={src}
          alt={alt}
          className="max-h-[80vh] max-w-[85vw] rounded-xl border border-border-subtle shadow-2xl object-contain"
        />
        <div className="flex items-center gap-3">
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-glass border border-border-subtle px-3 py-1.5 text-xs font-semibold text-primary hover:border-border-active"
          >
            Open in new tab
          </a>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1.5 rounded-lg bg-glass border border-border-subtle px-3 py-1.5 text-xs font-semibold text-primary hover:border-border-active"
          >
            Close
          </button>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-surface border border-border-subtle text-primary shadow-lg hover:bg-glass text-lg leading-none"
          aria-label="Close"
        >
          &times;
        </button>
      </div>
    </div>
  );
}

function FrameThumb({
  src,
  alt,
  onOpen,
}: {
  src: string | null;
  alt: string;
  onOpen: (src: string, alt: string) => void;
}) {
  if (!src) {
    return (
      <div className="h-48 w-[8.5rem] rounded-lg border border-dashed border-border-subtle bg-glass/50 flex items-center justify-center text-xs text-muted px-2 text-center">
        {alt}
      </div>
    );
  }
  return (
    <button
      type="button"
      className="group relative cursor-pointer rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      onClick={() => onOpen(src, alt)}
    >
      <img
        src={src}
        alt={alt}
        className="h-48 w-[8.5rem] object-cover rounded-lg border border-border-subtle bg-black/20 transition-transform group-hover:scale-[1.02] group-hover:shadow-lg"
      />
      <span className="absolute inset-0 flex items-center justify-center rounded-lg bg-black/0 group-hover:bg-black/40 transition-colors">
        <span className="opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs font-semibold bg-black/60 rounded-md px-2 py-1">
          View
        </span>
      </span>
    </button>
  );
}

export function FramesPage() {
  const { projectId = "" } = useParams();
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: planSet, isLoading: planLoading } = useScenePlan(projectId);
  const { data: renders, isLoading: rendersLoading } = useRenders(projectId);
  const startRender = useStartRender(projectId);
  const approvePair = useApproveFramePair(projectId);
  const regeneratePair = useRegenerateFramePair(projectId);
  const retryStep = useRetryRenderStep(projectId);
  const generateNarration = useGenerateNarration(projectId);
  const { data: executionPolicy } = useProviderExecutionPolicy();
  const { data: quickCreateStatus } = useQuickCreateStatus(projectId);

  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null);
  const openLightbox = useCallback((src: string, alt: string) => setLightbox({ src, alt }), []);

  const speechConfigured =
    !!executionPolicy?.speech?.credentialId || executionPolicy?.speech?.mode === "hosted";

  const hitlBusy = approvePair.isPending || regeneratePair.isPending || retryStep.isPending;

  const activeRender = useMemo(() => {
    if (!planSet?.id) return null;
    return latestRenderForPlan(renders, planSet.id);
  }, [planSet?.id, renders]);

  const quickCreateBanner =
    quickCreateStatus && (quickCreateStatus.isActive || quickCreateStatus.hasFailed)
      ? quickCreateStatus
      : null;

  const showHostedImageHint =
    !isMockMode() && executionPolicy?.image?.mode === "hosted" && planSet?.approvalState === "approved";

  if (isMockMode()) {
    return (
      <PageFrame
        eyebrow="Keyframes"
        title="Keyframe review"
        description="Connect the app to the live API to generate start and end frames, approve them, and continue to renders. The mock studio does not simulate the frame pipeline."
        inspector={<EmptyState title="Mock mode" description="Use live API for this step." />}
      >
        <div className="flex flex-wrap gap-3">
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-glass border border-border-subtle text-primary hover:border-border-active"
            to={`/app/projects/${projectId}/scenes`}
          >
            ← Scenes
          </Link>
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
            to={`/app/projects/${projectId}/renders`}
          >
            Renders →
          </Link>
        </div>
      </PageFrame>
    );
  }

  if (projectLoading || !project) {
    return <LoadingPage />;
  }

  if (planLoading || rendersLoading) {
    return <LoadingPage />;
  }

  if (!planSet || planSet.approvalState !== "approved") {
    return (
      <PageFrame
        eyebrow="Keyframes"
        title={`${project.title} · keyframes`}
        description="Approve the scene plan first, then generate start and end images per scene."
        inspector={<EmptyState title="Scene plan" description="Approval required before keyframes." />}
      >
        <Link
          className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
          to={`/app/projects/${projectId}/scenes`}
        >
          Open scene plan
        </Link>
      </PageFrame>
    );
  }

  const anyReview =
    activeRender?.steps.some(
      (s) => s.stepKind === "frame_pair_generation" && s.backendStatus === "review",
    ) ?? false;
  const allFramePairsApproved =
    planSet.scenes.length > 0 &&
    planSet.scenes.every((scene) => {
      const step = activeRender ? frameStepForScene(activeRender, scene.id) : undefined;
      return step?.backendStatus === "approved";
    });

  const renderFailed = activeRender?.status === "failed";
  const failedStep = activeRender && renderFailed ? firstFailedStep(activeRender) : undefined;
  const failureDetail =
    (activeRender?.errorMessage || failedStep?.errorMessage || "").trim() ||
    (activeRender?.errorCode || failedStep?.errorCode
      ? `Code: ${activeRender?.errorCode || failedStep?.errorCode}`
      : "");
  const failureSummary =
    failureDetail.slice(0, 160) + (failureDetail.length > 160 ? "…" : "") ||
    "Keyframe step failed — use Retry or check API/worker logs.";

  return (
    <PageFrame
      eyebrow="Keyframe generation"
      title={`${project.title} · frames`}
      description="Scene 1 uses your plan and visual preset only. Later scenes chain from the previous scene’s end frame. Approve each pair when it looks right, or regenerate to rerun the image route."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-glass border border-border-subtle text-primary hover:border-border-active"
            to={`/app/projects/${projectId}/scenes`}
          >
            ← Scenes
          </Link>
          {!activeRender ? (
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
              disabled={startRender.isPending}
              onClick={() => startRender.mutate(undefined)}
            >
              {startRender.isPending ? "Starting…" : "Generate keyframes"}
            </button>
          ) : renderFailed && failedStep ? (
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
              disabled={retryStep.isPending}
              onClick={() => retryStep.mutate(failedStep.id)}
            >
              {retryStep.isPending ? "Retrying…" : "Retry failed step"}
            </button>
          ) : renderFailed && !failedStep ? (
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
              disabled={startRender.isPending}
              onClick={() => startRender.mutate(undefined)}
            >
              {startRender.isPending ? "Starting…" : "New render"}
            </button>
          ) : allFramePairsApproved && activeRender.status !== "review" ? (
            <Link
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
              to={`/app/projects/${projectId}/renders`}
            >
              Open renders →
            </Link>
          ) : null}
        </div>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Pipeline">
            <div className="inspector-list">
              <div>
                <span>Render job</span>
                <strong>{activeRender ? activeRender.label : "Not started"}</strong>
              </div>
              {activeRender ? (
                <div>
                  <span>Status</span>
                  <strong>
                    <StatusBadge status={activeRender.status} />
                  </strong>
                </div>
              ) : null}
              {anyReview ? (
                <div>
                  <span>Review</span>
                  <strong className="text-warning">Awaiting frame approval</strong>
                </div>
              ) : null}
              {renderFailed ? (
                <div>
                  <span>Error</span>
                  <strong className="text-error text-xs font-normal leading-snug block mt-1 max-w-[28ch]">
                    {failureSummary}
                  </strong>
                </div>
              ) : null}
            </div>
          </SectionCard>
        </div>
      }
    >
      {quickCreateBanner ? <QuickStartStatusBanner status={quickCreateBanner} compact /> : null}

      {showHostedImageHint ? (
        <div className="rounded-xl border border-border-subtle bg-glass/80 px-4 py-3 text-sm text-secondary mb-4">
          <strong className="text-primary">Image route:</strong> this workspace uses{" "}
          <span className="text-primary font-medium">hosted</span> image generation. For your own model and keys, set
          the image route to <span className="text-primary font-medium">Bring your own</span> under{" "}
          <Link className="text-accent underline-offset-2 hover:underline" to="/app/settings/providers">
            Provider settings
          </Link>
          .
        </div>
      ) : null}

      {!activeRender ? (
        <SectionCard
          title="Ready to generate"
          subtitle="Creates a render job and produces start/end stills per scene. Scene 1 has no prior-frame reference; each following scene uses the previous end frame for continuity."
        >
          <p className="text-secondary text-sm max-w-[72ch] leading-relaxed mb-4">
            This step runs your workspace image provider with a composed prompt (visual preset, scene context, and
            continuity instructions). After all pairs are approved, the pipeline continues with video and composition
            on the Renders page.
          </p>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent"
            disabled={startRender.isPending}
            onClick={() => startRender.mutate(undefined)}
          >
            {startRender.isPending ? "Starting…" : "Generate keyframes"}
          </button>
        </SectionCard>
      ) : (
        <div className="flex flex-col gap-4">
          {renderFailed ? (
            <div className="rounded-xl border border-error-bg bg-error-bg/20 px-4 py-3 text-sm text-secondary">
              <p className="font-semibold text-error">Keyframe generation failed</p>
              {failureDetail ? (
                <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-glass/80 p-2 text-[11px] text-primary whitespace-pre-wrap break-words border border-border-subtle">
                  {failureDetail}
                </pre>
              ) : (
                <p className="mt-1 text-xs text-muted">
                  No error details were returned. Confirm the frame worker is running and image credentials are valid.
                </p>
              )}
              {retryStep.isError && retryStep.error instanceof Error ? (
                <p className="mt-2 text-xs text-error font-medium">{retryStep.error.message}</p>
              ) : null}
              {failedStep ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-accent-gradient px-3 py-2 text-xs font-semibold text-on-accent shadow-sm hover:shadow-accent"
                    disabled={retryStep.isPending}
                    onClick={() => retryStep.mutate(failedStep.id)}
                  >
                    {retryStep.isPending ? "Retrying…" : "Retry failed step"}
                  </button>
                  <p className="text-[11px] text-muted self-center max-w-[min(100%,42ch)]">
                    Re-queues this scene and everything after it. You can also use <strong className="text-primary">Retry</strong> on the
                    scene card below.
                  </p>
                </div>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-accent-gradient px-3 py-2 text-xs font-semibold text-on-accent shadow-sm hover:shadow-accent"
                    disabled={startRender.isPending}
                    onClick={() => startRender.mutate(undefined)}
                  >
                    {startRender.isPending ? "Starting…" : "New render"}
                  </button>
                  <p className="text-[11px] text-muted self-center max-w-[min(100%,42ch)]">
                    No individual step was marked failed. Creates a fresh render job with the same scene plan.
                  </p>
                </div>
              )}
            </div>
          ) : null}
          {planSet.scenes.map((scene) => {
            const step = activeRender ? frameStepForScene(activeRender, scene.id) : undefined;
            const start = activeRender ? assetUrl(activeRender, scene.id, "scene_start_frame") : null;
            const end = activeRender ? assetUrl(activeRender, scene.id, "scene_end_frame") : null;
            const inReview = step?.backendStatus === "review";
            const approved = step?.backendStatus === "approved";
            const stepFailed = step?.backendStatus === "failed";

            return (
              <SectionCard
                key={scene.id}
                title={`Scene ${scene.index}`}
                subtitle={scene.title}
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex flex-wrap gap-4">
                    <figure className="text-center">
                      <FrameThumb src={start} alt="Start frame pending" onOpen={(s) => openLightbox(s, `Scene ${scene.index} – Start`)} />
                      <figcaption className="text-[11px] text-muted mt-1">Start</figcaption>
                    </figure>
                    <figure className="text-center">
                      <FrameThumb src={end} alt="End frame pending" onOpen={(s) => openLightbox(s, `Scene ${scene.index} – End`)} />
                      <figcaption className="text-[11px] text-muted mt-1">End</figcaption>
                    </figure>
                  </div>
                  <div className="flex flex-col gap-2 min-w-[200px]">
                    {!step ? (
                      <p className="text-sm text-secondary">Waiting for this scene in the pipeline…</p>
                    ) : (
                      <>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted">Step</span>
                          <StatusBadge status={step.status} />
                        </div>
                        {stepFailed ? (
                          <div className="flex flex-col gap-1">
                            <p className="text-sm text-error font-medium">This step failed</p>
                            {step.errorMessage ? (
                              <p className="text-xs text-secondary max-w-[42ch] leading-relaxed break-words">
                                {step.errorMessage}
                              </p>
                            ) : null}
                            <button
                              type="button"
                              className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-accent-gradient px-3 py-2 text-xs font-semibold text-on-accent shadow-sm hover:shadow-accent mt-1 self-start"
                              disabled={retryStep.isPending}
                              onClick={() => retryStep.mutate(step.id)}
                            >
                              {retryStep.isPending ? "Retrying…" : "Retry this scene"}
                            </button>
                          </div>
                        ) : null}
                      </>
                    )}
                    {inReview && step ? (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-accent-gradient px-3 py-2 text-xs font-semibold text-on-accent shadow-sm hover:shadow-accent"
                          disabled={hitlBusy}
                          onClick={() => approvePair.mutate(step.id)}
                        >
                          Approve pair
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-glass px-3 py-2 text-xs font-semibold text-primary hover:border-border-active"
                          disabled={hitlBusy}
                          onClick={() => regeneratePair.mutate(step.id)}
                        >
                          Regenerate
                        </button>
                      </div>
                    ) : null}
                    {approved ? (
                      <span className="text-xs font-semibold text-success">Approved</span>
                    ) : null}
                  </div>
                </div>
                {activeRender ? (
                  <NarrationCard
                    audioSrc={narrationUrl(activeRender, scene.id)}
                    sceneId={scene.id}
                    renderJobId={activeRender.id}
                    speechConfigured={speechConfigured}
                    generateNarration={generateNarration.mutate}
                    isGenerating={
                      generateNarration.isPending &&
                      generateNarration.variables?.sceneSegmentId === scene.id
                    }
                  />
                ) : null}
              </SectionCard>
            );
          })}
        </div>
      )}

      {lightbox ? (
        <FrameLightbox src={lightbox.src} alt={lightbox.alt} onClose={() => setLightbox(null)} />
      ) : null}
    </PageFrame>
  );
}
