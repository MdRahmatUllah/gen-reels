import { useState, useCallback, useMemo, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useScenePlan, useGenerateScenePlan, useGeneratePromptPairs, useUpdateScene, useApproveScenePlan, useSetScenePlanPreset } from "../../hooks/use-scenes";
import { useVisualPresets, useVoicePresets } from "../../hooks/use-presets";
import type { ScenePlan, ScenePlanSet } from "../../types/domain";
import { CommentThread } from "../../components/CommentThread";
import { ConflictResolutionModal } from "../../components/ConflictResolutionModal";
import { mockUpdateScene } from "../../lib/mock-service";

/* ─── Shimmer placeholder ─────────────────────────────────────────────────── */
function SceneShimmer() {
  return (
    <div className="scene-shimmer" aria-label="Generating scene plan…">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="shimmer-card" style={{ animationDelay: `${i * 120}ms` }}>
          <div className="shimmer-line shimmer-line--title" />
          <div className="shimmer-line shimmer-line--body" />
          <div className="shimmer-line shimmer-line--body shimmer-line--short" />
        </div>
      ))}
      <p className="shimmer-label">Segmenting script and generating scene plan…</p>
    </div>
  );
}

/* ─── Duration badge ──────────────────────────────────────────────────────── */
function DurationBadge({ seconds, warning }: { seconds: number; warning: string | null }) {
  return (
    <span className={`duration-badge ${warning ? "duration-badge--warning" : ""}`} title={warning ?? undefined}>
      {seconds.toFixed(1)}s
      {warning ? " ⚠" : ""}
    </span>
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
          className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
          onClick={onGenerate}
          disabled={isGenerating || isApproved}
          style={{ minHeight: "2rem", padding: "0.4rem 0.8rem", fontSize: "0.8rem" }}
        >
          {isGenerating ? "Generating…" : "Generate prompts"}
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
            placeholder="Describe the opening frame of this scene…"
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
            placeholder="Describe the closing frame and transition…"
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
        <span className="scene-detail-editor__preview-label">{scene.thumbnailLabel}</span>
        <span className="scene-detail-editor__preview-meta">{scene.shotType} · {scene.motion}</span>
      </div>

      {/* Core fields */}
      <div className="scene-detail-editor__fields">
        <div className="content-grid content-grid--equal">
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-title-${scene.id}`}>Title</label>
            <input
              id={`scene-title-${scene.id}`}
              className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
              value={localScene.title}
              onChange={(e) => handleFieldChange("title", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-shot-${scene.id}`}>Shot type</label>
            <input
              id={`scene-shot-${scene.id}`}
              className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
              value={localScene.shotType}
              onChange={(e) => handleFieldChange("shotType", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
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
              className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
              value={localScene.motion}
              onChange={(e) => handleFieldChange("motion", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
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
              className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
              value={localScene.palette}
              onChange={(e) => handleFieldChange("palette", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
          <div className="form-field">
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor={`scene-audio-${scene.id}`}>Audio cue</label>
            <input
              id={`scene-audio-${scene.id}`}
              className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
              value={localScene.audioCue}
              onChange={(e) => handleFieldChange("audioCue", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
        </div>
      </div>

      {/* Duration display */}
      <div className="scene-detail-editor__duration">
        <div className="duration-display">
          <span className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1">EST. DURATION</span>
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

      {/* Save */}
      {dirty && !isApproved ? (
        <div className="scene-detail-editor__actions">
          <button type="button" className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" onClick={() => { setLocalScene(scene); setDirty(false); }}>
            Discard
          </button>
          <button type="button" className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" onClick={handleSave} disabled={updateScene.isPending}>
            {updateScene.isPending ? "Saving…" : "Save changes"}
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
          className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
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
          className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
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

/* ─── Main ScenesPage ─────────────────────────────────────────────────────── */
export function ScenesPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const { data: planSet, isLoading } = useScenePlan(projectId);
  const generatePlan = useGenerateScenePlan(projectId);
  const approvePlan = useApproveScenePlan(projectId);

  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);

  // Auto-select first scene
  useEffect(() => {
    if (planSet?.scenes.length && !selectedSceneId) {
      setSelectedSceneId(planSet.scenes[0].id);
    }
  }, [planSet, selectedSceneId]);

  const selectedScene = useMemo(() => {
    if (!planSet) return null;
    return planSet.scenes.find((s) => s.id === selectedSceneId) ?? planSet.scenes[0] ?? null;
  }, [planSet, selectedSceneId]);

  const isApproved = planSet?.approvalState === "approved";
  const hasPlan = planSet && planSet.scenes.length > 0;

  const handleGenerate = useCallback(() => {
    generatePlan.mutate(undefined, {
      onSuccess: (result) => {
        if (result.scenes.length > 0) setSelectedSceneId(result.scenes[0].id);
      },
    });
  }, [generatePlan]);

  const handleApprove = useCallback(() => {
    approvePlan.mutate(undefined, {
      onSuccess: () => navigate(`/app/projects/${projectId}/renders`),
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

  /* ─── Empty state ─────────────────────────────────────────────────────── */
  if (!isLoading && !hasPlan && !generatePlan.isPending) {
    return (
      <div className="scene-empty-state">
        <div className="scene-empty-state__card">
          <div className="scene-empty-state__icon">🎬</div>
          <h2>No scene plan yet</h2>
          <p>Generate a scene plan from the approved script. The system will segment it into scenes, assign shot types, and create start/end frame prompts.</p>
          <button type="button" className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" onClick={handleGenerate}>
            Generate scene plan
          </button>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${projectId}/script`}>
            ← Back to script
          </Link>
        </div>
      </div>
    );
  }

  /* ─── Loading state ───────────────────────────────────────────────────── */
  if (isLoading || generatePlan.isPending) {
    return (
      <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
        <SceneShimmer />
      </div>
    );
  }

  if (!planSet || !selectedScene) return null;

  /* ─── Main layout ─────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
      {/* Header */}
      <div className="flex items-end justify-between gap-6">
        <div>
          <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Scene planner</p>
          <h1 className="font-heading text-3xl md:text-4xl leading-tight font-bold text-primary tracking-tight">Scene plan</h1>
          <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
            {planSet.scenes.length} scenes · {planSet.totalDurationSec.toFixed(1)}s total
            {planSet.warningsCount > 0 ? ` · ${planSet.warningsCount} warning${planSet.warningsCount > 1 ? "s" : ""}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${projectId}/script`}>
            ← Script
          </Link>
          {!isApproved ? (
            <>
              <button type="button" className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" onClick={triggerGhostEdit}>
                Trigger Ghost Edit
              </button>
              <button type="button" className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" onClick={handleGenerate} disabled={generatePlan.isPending}>
                Regenerate plan
              </button>
              <button type="button" className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" onClick={handleApprove} disabled={approvePlan.isPending}>
                {approvePlan.isPending ? "Approving…" : "Approve scene plan →"}
              </button>
            </>
          ) : (
            <span className="approval-badge approval-badge--approved">✓ Approved</span>
          )}
        </div>
      </div>

      {/* Three-column layout */}
      <div className="scene-workspace">
        {/* Timeline sidebar */}
        <div className="scene-timeline">
          <div className="scene-timeline__header">
            <h3 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Timeline</h3>
            <span className="text-muted" style={{ fontSize: "0.75rem" }}>
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
          <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in">
            <h3 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Plan status</h3>
            <div className="inspector-list">
              <div>
                <span>Approval</span>
                <strong>{isApproved ? "Approved" : "Draft"}</strong>
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

          <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in">
            <h3 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Presets</h3>
            <PresetPicker projectId={projectId} planSet={planSet} />
          </div>

          {selectedScene ? (
            <>
              <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in">
                <h3 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Scene {selectedScene.index}</h3>
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
            
            <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in">
              <h3 className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Prompt Lineage</h3>
              {(!selectedScene.promptHistory || selectedScene.promptHistory.length === 0) ? (
                <p className="text-xs text-muted">No previous prompt versions logged.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                  {selectedScene.promptHistory.map((h, i) => (
                    <div key={i} className="rounded-lg border border-dashed border-border-card bg-card px-3 py-2 text-[11px] leading-[1.4] text-muted">
                      {h}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <CommentThread targetId={selectedScene.id} />
          </>
        ) : null}
      </div>
      </div>
    </div>
  );
}
