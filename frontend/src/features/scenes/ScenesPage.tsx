import { useState, useCallback, useMemo, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useScenePlan, useGenerateScenePlan, useGeneratePromptPairs, useUpdateScene, useApproveScenePlan, useSetScenePlanPreset } from "../../hooks/use-scenes";
import { useProviderExecutionPolicy } from "../../hooks/use-providers";
import { useVisualPresets, useVoicePresets } from "../../hooks/use-presets";
import { useQuickCreateStatus } from "../../hooks/use-projects";
import type { ScenePlan, ScenePlanSet } from "../../types/domain";
import { CommentThread } from "../../components/CommentThread";
import { ConflictResolutionModal } from "../../components/ConflictResolutionModal";
import { mockUpdateScene } from "../../lib/mock-service";
import { isMockMode } from "../../lib/config";
import { QuickStartStatusBanner } from "../projects/quick-start";

/* ─── Icons ───────────────────────────────────────────────────────────────── */
function SparklesIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
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

function CheckIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function FilmIcon({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
      <path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5" />
    </svg>
  );
}

function RefreshIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M23 4v6h-6M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
  );
}

/* ─── Shimmer placeholder ─────────────────────────────────────────────────── */
function SceneShimmer() {
  return (
    <div className="flex flex-col gap-5" aria-label="Generating scene plan...">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-5 h-5 border-[3px] border-border-subtle border-t-accent rounded-full animate-spin shrink-0" />
        <span className="text-sm font-semibold text-secondary">Segmenting script and generating scene plan...</span>
      </div>
      <div className="scene-workspace">
        <div className="scene-timeline">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-glass" style={{ animationDelay: `${i * 100}ms` }}>
              <div className="shimmer h-8 w-8 rounded-full shrink-0" />
              <div className="flex-1 flex flex-col gap-2">
                <div className="shimmer h-3 w-3/4 rounded-full" />
                <div className="shimmer h-2.5 w-1/2 rounded-full" />
              </div>
            </div>
          ))}
        </div>
        <div className="scene-detail">
          <div className="shimmer h-48 rounded-2xl" />
          <div className="flex flex-col gap-3 mt-4">
            <div className="shimmer h-4 w-1/3 rounded-full" />
            <div className="shimmer h-3 w-full rounded-full" />
            <div className="shimmer h-3 w-5/6 rounded-full" />
          </div>
        </div>
        <div className="scene-inspector">
          <div className="shimmer h-40 rounded-xl" />
          <div className="shimmer h-32 rounded-xl" />
        </div>
      </div>
    </div>
  );
}

/* ─── Duration badge ──────────────────────────────────────────────────────── */
function DurationBadge({ seconds, warning }: { seconds: number; warning: string | null }) {
  return (
    <span className={`duration-badge ${warning ? "duration-badge--warning" : ""}`} title={warning ?? undefined}>
      {seconds.toFixed(1)}s
      {warning ? " !" : ""}
    </span>
  );
}

/* ─── Continuity Score Bar ────────────────────────────────────────────────── */
function ContinuityBar({ score }: { score: number }) {
  const color =
    score >= 90
      ? "var(--success-fg)"
      : score >= 70
        ? "var(--accent)"
        : score >= 50
          ? "var(--warning-fg)"
          : "var(--error-fg)";

  return (
    <div className="scene-continuity-bar">
      <div
        className="scene-continuity-bar__fill"
        style={{
          width: `${score}%`,
          backgroundColor: color,
          boxShadow: score >= 80 ? `0 0 6px ${color}` : "none",
        }}
      />
    </div>
  );
}

/* ─── Timeline Item ───────────────────────────────────────────────────────── */
function TimelineSceneItem({ scene, active, onClick }: { scene: ScenePlan; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      className={`timeline-scene-item ${active ? "timeline-scene-item--active" : ""}`}
      onClick={onClick}
    >
      <span className="timeline-scene-item__index">{scene.index}</span>
      <div className="timeline-scene-item__info">
        <strong>{scene.title}</strong>
        <span className="timeline-scene-item__meta">
          {scene.shotType} · <DurationBadge seconds={scene.durationSec} warning={scene.durationWarning} />
        </span>
        <ContinuityBar score={scene.continuityScore} />
      </div>
      <span className={`status-dot status-dot--${scene.status}`} />
    </button>
  );
}

/* ─── Prompt Pair Editor ──────────────────────────────────────────────────── */
function PromptPairEditor({
  scene,
  onUpdate,
  onGenerate,
  isGenerating,
  isApproved,
}: {
  scene: ScenePlan;
  onUpdate: (field: "startImagePrompt" | "endImagePrompt", value: string) => void;
  onGenerate: () => void;
  isGenerating: boolean;
  isApproved: boolean;
}) {
  return (
    <div className="prompt-pair-editor">
      <div className="prompt-pair-editor__header">
        <h4 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Frame prompts</h4>
        <button
          type="button"
          className="btn-ghost"
          onClick={onGenerate}
          disabled={isGenerating || isApproved}
          style={{ minHeight: "2rem", padding: "0.4rem 0.8rem", fontSize: "0.8rem" }}
        >
          <SparklesIcon size={13} />
          {isGenerating ? "Generating..." : "Generate prompts"}
        </button>
      </div>
      <div className="prompt-pair-editor__grid">
        <div className="form-field">
          <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`start-prompt-${scene.id}`}>Start frame</label>
          <textarea
            id={`start-prompt-${scene.id}`}
            className="field-input field-textarea"
            value={scene.startImagePrompt}
            onChange={(e) => onUpdate("startImagePrompt", e.target.value)}
            rows={4}
            placeholder="Describe the opening frame of this scene..."
            disabled={isApproved}
          />
        </div>
        <div className="form-field">
          <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`end-prompt-${scene.id}`}>End frame</label>
          <textarea
            id={`end-prompt-${scene.id}`}
            className="field-input field-textarea"
            value={scene.endImagePrompt}
            onChange={(e) => onUpdate("endImagePrompt", e.target.value)}
            rows={4}
            placeholder="Describe the closing frame and transition..."
            disabled={isApproved}
          />
        </div>
      </div>
    </div>
  );
}

/* ─── Scene Detail Editor ─────────────────────────────────────────────────── */
function SceneDetailEditor({
  scene,
  projectId,
  isApproved,
}: {
  scene: ScenePlan;
  projectId: string;
  isApproved: boolean;
}) {
  const updateScene = useUpdateScene(projectId);
  const generatePromptPairs = useGeneratePromptPairs(projectId);

  const [localScene, setLocalScene] = useState(scene);
  const [dirty, setDirty] = useState(false);
  const [conflictData, setConflictData] = useState<{ serverVersion: ScenePlan; clientVersion: ScenePlan } | null>(null);

  useEffect(() => {
    setLocalScene(scene);
    setDirty(false);
    setConflictData(null);
  }, [scene]);

  const handleFieldChange = useCallback((field: keyof ScenePlan, value: string | number) => {
    setLocalScene((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  }, []);

  const handleSave = useCallback(async () => {
    try {
      await updateScene.mutateAsync({ sceneId: scene.id, updates: localScene });
      setDirty(false);
      setConflictData(null);
    } catch (err: any) {
      if (err?.status === 409) {
        setConflictData({
          serverVersion: err.currentVersion,
          clientVersion: localScene,
        });
      } else {
        alert("Failed to save changes.");
      }
    }
  }, [localScene, scene.id, updateScene]);

  const handleResolveConflict = useCallback((resolvedVersion: ScenePlan) => {
    updateScene.mutate({ sceneId: scene.id, updates: resolvedVersion });
    setLocalScene(resolvedVersion);
    setDirty(false);
    setConflictData(null);
  }, [scene.id, updateScene]);

  const handlePromptUpdate = useCallback((field: "startImagePrompt" | "endImagePrompt", value: string) => {
    handleFieldChange(field, value);
  }, [handleFieldChange]);

  const handleGeneratePrompts = useCallback(() => {
    generatePromptPairs.mutate(scene.id);
  }, [generatePromptPairs, scene.id]);

  return (
    <div className="scene-detail-editor">
      {/* Media preview */}
      <div className="scene-detail-editor__preview" style={{ background: scene.gradient }}>
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
        <div className="relative z-10">
          <span className="scene-detail-editor__preview-label">{scene.thumbnailLabel}</span>
          <span className="scene-detail-editor__preview-meta">{scene.shotType} · {scene.motion}</span>
        </div>
      </div>

      {/* Core fields */}
      <div className="scene-detail-editor__fields">
        <div className="content-grid content-grid--equal">
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-title-${scene.id}`}>Title</label>
            <input
              id={`scene-title-${scene.id}`}
              className="field-input"
              value={localScene.title}
              onChange={(e) => handleFieldChange("title", e.target.value)}
              disabled={isApproved}
            />
          </div>
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-shot-${scene.id}`}>Shot type</label>
            <input
              id={`scene-shot-${scene.id}`}
              className="field-input"
              value={localScene.shotType}
              onChange={(e) => handleFieldChange("shotType", e.target.value)}
              disabled={isApproved}
            />
          </div>
        </div>

        <div className="form-field">
          <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-beat-${scene.id}`}>Beat / narration</label>
          <textarea
            id={`scene-beat-${scene.id}`}
            className="field-input field-textarea"
            value={localScene.narration}
            onChange={(e) => handleFieldChange("narration", e.target.value)}
            rows={3}
            disabled={isApproved}
          />
        </div>

        <div className="content-grid content-grid--equal">
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-motion-${scene.id}`}>Camera motion</label>
            <input
              id={`scene-motion-${scene.id}`}
              className="field-input"
              value={localScene.motion}
              onChange={(e) => handleFieldChange("motion", e.target.value)}
              disabled={isApproved}
            />
          </div>
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1">Transition</label>
            <div className="transition-picker">
              {(["hard_cut", "crossfade"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={`chip-button ${localScene.transitionMode === mode ? "chip-button--active" : ""}`}
                  onClick={() => handleFieldChange("transitionMode", mode)}
                  disabled={isApproved}
                >
                  {mode === "hard_cut" ? "Hard cut" : "Crossfade"}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="content-grid content-grid--equal">
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-palette-${scene.id}`}>Palette</label>
            <input
              id={`scene-palette-${scene.id}`}
              className="field-input"
              value={localScene.palette}
              onChange={(e) => handleFieldChange("palette", e.target.value)}
              disabled={isApproved}
            />
          </div>
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-audio-${scene.id}`}>Audio cue</label>
            <input
              id={`scene-audio-${scene.id}`}
              className="field-input"
              value={localScene.audioCue}
              onChange={(e) => handleFieldChange("audioCue", e.target.value)}
              disabled={isApproved}
            />
          </div>
        </div>
      </div>

      {/* Duration display */}
      <div className="scene-detail-editor__duration">
        <div className="duration-display">
          <span className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1">Est. duration</span>
          <strong className={scene.durationWarning ? "text-warning" : ""}>
            {scene.durationSec.toFixed(1)}s
          </strong>
          <span className="text-muted">{scene.estimatedWordCount} words</span>
        </div>
        {scene.durationWarning ? (
          <p className="duration-warning">{scene.durationWarning}</p>
        ) : null}
      </div>

      {/* Prompt pair editor */}
      <PromptPairEditor
        scene={localScene}
        onUpdate={handlePromptUpdate}
        onGenerate={handleGeneratePrompts}
        isGenerating={generatePromptPairs.isPending}
        isApproved={isApproved}
      />

      {/* Save / Discard */}
      {dirty && !isApproved ? (
        <div className="scene-detail-editor__actions">
          <button type="button" className="btn-ghost" onClick={() => { setLocalScene(scene); setDirty(false); }}>
            Discard
          </button>
          <button type="button" className="btn-primary" onClick={handleSave} disabled={updateScene.isPending}>
            <CheckIcon size={14} />
            {updateScene.isPending ? "Saving..." : "Save changes"}
          </button>
        </div>
      ) : null}

      {conflictData && (
        <ConflictResolutionModal
          serverVersion={conflictData.serverVersion}
          clientVersion={conflictData.clientVersion}
          onResolve={handleResolveConflict}
          onCancel={() => setConflictData(null)}
        />
      )}
    </div>
  );
}

/* ─── Preset Picker ───────────────────────────────────────────────────────── */
function PresetPicker({
  projectId,
  planSet,
}: {
  projectId: string;
  planSet: ScenePlanSet;
}) {
  const { data: visualPresets } = useVisualPresets();
  const { data: voicePresets } = useVoicePresets();
  const setPreset = useSetScenePlanPreset(projectId);

  return (
    <div className="preset-picker-section">
      <div className="form-field">
        <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="visual-preset-picker">Visual preset</label>
        <select
          id="visual-preset-picker"
          className="field-input"
          value={planSet.visualPresetId ?? ""}
          onChange={(e) => setPreset.mutate({ type: "visual", presetId: e.target.value })}
        >
          <option value="">None selected</option>
          {visualPresets?.map((p) => (
            <option key={p.id} value={p.id}>{p.name} — {p.description}</option>
          ))}
        </select>
      </div>
      <div className="form-field">
        <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="voice-preset-picker">Voice preset</label>
        <select
          id="voice-preset-picker"
          className="field-input"
          value={planSet.voicePresetId ?? ""}
          onChange={(e) => setPreset.mutate({ type: "voice", presetId: e.target.value })}
        >
          <option value="">None selected</option>
          {voicePresets?.map((p) => (
            <option key={p.id} value={p.id}>{p.name} — {p.description}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

/* ─── Continuity Score Ring ────────────────────────────────────────────────── */
function ContinuityRing({ score, size = 44 }: { score: number; size?: number }) {
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 90
      ? "var(--success-fg)"
      : score >= 70
        ? "var(--accent)"
        : score >= 50
          ? "var(--warning-fg)"
          : "var(--error-fg)";

  return (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
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
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
      </svg>
      <span className="absolute text-[0.75rem] font-bold text-primary font-heading">{score}</span>
    </div>
  );
}

/* ─── Main ScenesPage ─────────────────────────────────────────────────────── */
export function ScenesPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const { data: planSet, isLoading } = useScenePlan(projectId);
  const { data: executionPolicy } = useProviderExecutionPolicy();
  const generatePlan = useGenerateScenePlan(projectId);
  const approvePlan = useApproveScenePlan(projectId);
  const { data: quickCreateStatus } = useQuickCreateStatus(projectId);

  const showHostedImageHint =
    !isMockMode() && executionPolicy?.image?.mode === "hosted" && planSet?.approvalState === "approved";

  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [queuedGeneration, setQueuedGeneration] = useState(false);

  useEffect(() => {
    if (planSet?.scenes.length && !selectedSceneId) {
      setSelectedSceneId(planSet.scenes[0].id);
    }
  }, [planSet, selectedSceneId]);

  useEffect(() => {
    if ((planSet?.scenes.length ?? 0) > 0) {
      setQueuedGeneration(false);
    }
  }, [planSet?.scenes.length]);

  const selectedScene = useMemo(() => {
    if (!planSet) return null;
    return planSet.scenes.find((s) => s.id === selectedSceneId) ?? planSet.scenes[0] ?? null;
  }, [planSet, selectedSceneId]);

  const isApproved = planSet?.approvalState === "approved";
  const hasPlan = planSet && planSet.scenes.length > 0;
  const quickCreateBanner =
    quickCreateStatus && (quickCreateStatus.isActive || quickCreateStatus.hasFailed)
      ? quickCreateStatus
      : null;
  const isQuickCreateLocked = quickCreateStatus?.isActive ?? false;

  const handleGenerate = useCallback(() => {
    setQueuedGeneration(true);
    generatePlan.mutate();
  }, [generatePlan]);

  const handleApprove = useCallback(() => {
    approvePlan.mutate(undefined, {
      onSuccess: () => navigate(`/app/projects/${projectId}/frames`),
    });
  }, [approvePlan, navigate, projectId]);

  const triggerGhostEdit = useCallback(() => {
    if (planSet && planSet.scenes.length > 0) {
      const firstScene = planSet.scenes[0];
      mockUpdateScene(projectId, firstScene.id, {
        shotType: "Extra wide shot (GHOST EDIT)",
        version: firstScene.version + 1
      }).then(() => {
        alert("Ghost edit injected for Scene " + firstScene.index + " — please make an edit to Scene " + firstScene.index + " and try to save.");
      });
    }
  }, [planSet, projectId]);

  /* ── Empty state ──────────────────────────────────────────────────────── */
  if (!isLoading && !hasPlan && !generatePlan.isPending && !queuedGeneration && !isQuickCreateLocked) {
    return (
      <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
        <div className="scene-empty">
          <div className="scene-empty__icon">
            <FilmIcon />
          </div>
          <div className="flex flex-col gap-2 max-w-md">
            <h3 className="font-heading text-xl font-bold text-primary">Ready to plan your scenes</h3>
            <p className="text-[0.9rem] leading-relaxed text-secondary">
              Generate a scene plan from the approved script. The AI will segment it into scenes with shot types, camera motion, and frame prompts.
            </p>
          </div>
          <div className="flex flex-col gap-2 text-left max-w-sm w-full">
            {[
              { label: "Script segmentation", detail: "Breaks your script into timed scenes" },
              { label: "Shot planning", detail: "Assigns shot types and camera motion" },
              { label: "Frame prompts", detail: "Generates start/end image descriptions" },
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
          <div className="flex items-center gap-3 mt-2">
            <button type="button" className="btn-primary" onClick={handleGenerate}>
              <SparklesIcon />
              Generate scene plan
            </button>
            <Link className="btn-ghost" to={`/app/projects/${projectId}/script`}>
              Back to script
            </Link>
          </div>
        </div>
      </div>
    );
  }

  /* ── Loading / generating state ───────────────────────────────────────── */
  if (
    isLoading ||
    generatePlan.isPending ||
    queuedGeneration ||
    planSet?.status === "running" ||
    (!hasPlan && isQuickCreateLocked)
  ) {
    return (
      <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
        {quickCreateBanner ? <QuickStartStatusBanner status={quickCreateBanner} /> : null}
        <SceneShimmer />
      </div>
    );
  }

  if (!planSet || !selectedScene) return null;

  const avgContinuity = Math.round(
    planSet.scenes.reduce((sum, s) => sum + s.continuityScore, 0) / planSet.scenes.length
  );

  /* ── Main layout ──────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
      {/* Header */}
      <div className="flex items-end justify-between gap-6">
        <div className="flex flex-col gap-1.5">
          <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Scene planner</p>
          <h1 className="font-heading text-3xl md:text-4xl leading-tight font-bold text-primary tracking-tight">Scene plan</h1>
          <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
            {planSet.scenes.length} scenes · {planSet.totalDurationSec.toFixed(1)}s total
            {planSet.warningsCount > 0 ? ` · ${planSet.warningsCount} warning${planSet.warningsCount > 1 ? "s" : ""}` : ""}
            {` · ${avgContinuity}/100 avg continuity`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link className="btn-ghost" to={`/app/projects/${projectId}/script`}>
            Back to script
          </Link>
          {isQuickCreateLocked ? null : !isApproved ? (
            <>
              {isMockMode() ? (
                <button type="button" className="btn-ghost" onClick={triggerGhostEdit}>
                  Ghost Edit
                </button>
              ) : null}
              <button type="button" className="btn-ghost" onClick={handleGenerate} disabled={generatePlan.isPending}>
                <RefreshIcon size={14} />
                Regenerate
              </button>
              <button type="button" className="btn-primary" onClick={handleApprove} disabled={approvePlan.isPending}>
                <CheckIcon size={14} />
                {approvePlan.isPending ? "Approving..." : "Approve plan"}
              </button>
            </>
          ) : (
            <>
              <span className="approval-badge approval-badge--approved">Approved</span>
              <Link className="btn-primary" to={`/app/projects/${projectId}/frames`}>
                Keyframes
                <ArrowRightIcon />
              </Link>
            </>
          )}
        </div>
      </div>

      {quickCreateBanner ? <QuickStartStatusBanner status={quickCreateBanner} compact /> : null}

      {showHostedImageHint ? (
        <div className="rounded-xl border border-border-subtle bg-glass/80 px-4 py-3 text-sm text-secondary">
          <strong className="text-primary">Image generation route:</strong> this workspace is set to{" "}
          <span className="text-primary font-medium">hosted</span> image generation. To use the model and API key
          from <span className="text-primary font-medium">Settings &rarr; Providers</span>, switch the image route to{" "}
          <span className="text-primary font-medium">Bring your own</span> and activate your credential.{" "}
          <Link className="text-accent underline-offset-2 hover:underline" to="/app/settings/providers">
            Open provider settings
          </Link>
        </div>
      ) : null}

      {/* Stats ribbon */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Scenes", value: `${planSet.scenes.length}`, bg: "bg-primary-bg", fg: "text-primary-fg" },
          { label: "Total duration", value: `${planSet.totalDurationSec.toFixed(1)}s`, bg: "bg-[rgba(14,165,233,0.12)]", fg: "text-accent-secondary" },
          { label: "Avg continuity", value: `${avgContinuity}/100`, bg: avgContinuity >= 80 ? "bg-success-bg" : "bg-warning-bg", fg: avgContinuity >= 80 ? "text-success" : "text-warning" },
          { label: "Warnings", value: `${planSet.warningsCount}`, bg: planSet.warningsCount > 0 ? "bg-warning-bg" : "bg-success-bg", fg: planSet.warningsCount > 0 ? "text-warning" : "text-success" },
        ].map((stat) => (
          <div key={stat.label} className="stat-card animate-rise-in">
            <div className={`stat-card__icon ${stat.bg} ${stat.fg}`}>
              {stat.label === "Scenes" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" /><path d="M7 2v20M17 2v20M2 12h20" /></svg>
              ) : stat.label === "Total duration" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
              ) : stat.label === "Avg continuity" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><path d="M22 4L12 14.01l-3-3" /></svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" /></svg>
              )}
            </div>
            <div className="flex flex-col">
              <span className="stat-card__value">{stat.value}</span>
              <span className="stat-card__label">{stat.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Three-column workspace */}
      <div className="scene-workspace">
        {/* Timeline sidebar */}
        <div className="scene-timeline">
          <div className="scene-timeline__header">
            <h3 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Timeline</h3>
            <span className="text-[0.7rem] font-bold text-muted px-2 py-0.5 rounded-full bg-glass border border-border-subtle">
              {planSet.totalDurationSec.toFixed(1)}s
            </span>
          </div>
          <div className="scene-timeline__list">
            {planSet.scenes.map((scene) => (
              <TimelineSceneItem
                key={scene.id}
                scene={scene}
                active={scene.id === selectedSceneId}
                onClick={() => setSelectedSceneId(scene.id)}
              />
            ))}
          </div>
        </div>

        {/* Detail editor */}
        <div className="scene-detail">
          <SceneDetailEditor
            key={selectedScene.id}
            scene={selectedScene}
            projectId={projectId}
            isApproved={isApproved}
          />
        </div>

        {/* Inspector */}
        <div className="scene-inspector">
          <div className="scene-inspector-card">
            <h3 className="scene-inspector-card__title">Plan status</h3>
            <div className="inspector-list">
              <div>
                <span>Approval</span>
                <strong className={isApproved ? "text-success" : ""}>{isApproved ? "Approved" : "Draft"}</strong>
              </div>
              <div>
                <span>Scenes</span>
                <strong>{planSet.scenes.length}</strong>
              </div>
              <div>
                <span>Total duration</span>
                <strong>{planSet.totalDurationSec.toFixed(1)}s</strong>
              </div>
              <div>
                <span>Warnings</span>
                <strong className={planSet.warningsCount > 0 ? "text-warning" : ""}>{planSet.warningsCount}</strong>
              </div>
            </div>
          </div>

          <div className="scene-inspector-card">
            <h3 className="scene-inspector-card__title">Presets</h3>
            <PresetPicker projectId={projectId} planSet={planSet} />
          </div>

          {selectedScene ? (
            <>
              <div className="scene-inspector-card">
                <div className="flex items-center justify-between">
                  <h3 className="scene-inspector-card__title">Scene {selectedScene.index}</h3>
                  <ContinuityRing score={selectedScene.continuityScore} />
                </div>
                <div className="inspector-list">
                  <div>
                    <span>Continuity</span>
                    <strong>{selectedScene.continuityScore}/100</strong>
                  </div>
                  <div>
                    <span>Keyframe</span>
                    <strong>{selectedScene.keyframeStatus}</strong>
                  </div>
                  <div>
                    <span>Transition</span>
                    <strong>{selectedScene.transitionMode === "hard_cut" ? "Hard cut" : "Crossfade"}</strong>
                  </div>
                  <div>
                    <span>Subtitle</span>
                    <strong>{selectedScene.subtitleStatus}</strong>
                  </div>
                </div>
              </div>

              <div className="scene-inspector-card">
                <h3 className="scene-inspector-card__title">Prompt lineage</h3>
                {(!selectedScene.promptHistory || selectedScene.promptHistory.length === 0) ? (
                  <p className="text-xs text-muted">No previous prompt versions logged.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {selectedScene.promptHistory.map((h, i) => (
                      <div key={i} className="scene-lineage-item">
                        <span className="text-[0.65rem] font-bold text-muted uppercase tracking-wider">v{i + 1}</span>
                        <p className="mt-0.5">{h}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <CommentThread projectId={projectId} targetId={selectedScene.id} targetType="scene_segment" />
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
