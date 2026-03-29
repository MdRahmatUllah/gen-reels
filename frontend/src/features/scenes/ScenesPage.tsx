import { useState, useCallback, useMemo, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useScenePlan, useGenerateScenePlan, useGeneratePromptPairs, useUpdateScene, useApproveScenePlan, useSetScenePlanPreset } from "../../hooks/use-scenes";
import { useVisualPresets, useVoicePresets } from "../../hooks/use-presets";
import type { ScenePlan, ScenePlanSet } from "../../types/domain";

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
        <h4 className="section-heading">Frame prompts</h4>
        <button
          type="button"
          className="button button--secondary"
          onClick={onGenerate}
          disabled={isGenerating || isApproved}
          style={{ minHeight: "2rem", padding: "0.4rem 0.8rem", fontSize: "0.8rem" }}
        >
          {isGenerating ? "Generating…" : "Generate prompts"}
        </button>
      </div>
      <div className="prompt-pair-editor__grid">
        <div className="form-field">
          <label className="field-label" htmlFor={`start-prompt-${scene.id}`}>Start frame</label>
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
          <label className="field-label" htmlFor={`end-prompt-${scene.id}`}>End frame</label>
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

  useEffect(() => {
    setLocalScene(scene);
    setDirty(false);
  }, [scene]);

  const handleFieldChange = useCallback((field: keyof ScenePlan, value: string | number) => {
    setLocalScene((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  }, []);

  const handleSave = useCallback(() => {
    updateScene.mutate({ sceneId: scene.id, updates: localScene });
    setDirty(false);
  }, [localScene, scene.id, updateScene]);

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
            <label className="field-label" htmlFor={`scene-title-${scene.id}`}>Title</label>
            <input
              id={`scene-title-${scene.id}`}
              className="field-input"
              value={localScene.title}
              onChange={(e) => handleFieldChange("title", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
          <div className="form-field">
            <label className="field-label" htmlFor={`scene-shot-${scene.id}`}>Shot type</label>
            <input
              id={`scene-shot-${scene.id}`}
              className="field-input"
              value={localScene.shotType}
              onChange={(e) => handleFieldChange("shotType", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
        </div>

        <div className="form-field">
          <label className="field-label" htmlFor={`scene-beat-${scene.id}`}>Beat / narration</label>
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
            <label className="field-label" htmlFor={`scene-motion-${scene.id}`}>Camera motion</label>
            <input
              id={`scene-motion-${scene.id}`}
              className="field-input"
              value={localScene.motion}
              onChange={(e) => handleFieldChange("motion", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
          <div className="form-field">
            <label className="field-label">Transition</label>
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
            <label className="field-label" htmlFor={`scene-palette-${scene.id}`}>Palette</label>
            <input
              id={`scene-palette-${scene.id}`}
              className="field-input"
              value={localScene.palette}
              onChange={(e) => handleFieldChange("palette", e.target.value)}
              disabled={isApproved}
              style={{ backgroundImage: "none", paddingRight: "0.85rem" }}
            />
          </div>
          <div className="form-field">
            <label className="field-label" htmlFor={`scene-audio-${scene.id}`}>Audio cue</label>
            <input
              id={`scene-audio-${scene.id}`}
              className="field-input"
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
          <span className="field-label">EST. DURATION</span>
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
          <button type="button" className="button button--secondary" onClick={() => { setLocalScene(scene); setDirty(false); }}>
            Discard
          </button>
          <button type="button" className="button button--primary" onClick={handleSave} disabled={updateScene.isPending}>
            {updateScene.isPending ? "Saving…" : "Save changes"}
          </button>
        </div>
      ) : null}
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
        <label className="field-label" htmlFor="visual-preset-picker">Visual preset</label>
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
        <label className="field-label" htmlFor="voice-preset-picker">Voice preset</label>
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

  /* ─── Empty state ─────────────────────────────────────────────────────── */
  if (!isLoading && !hasPlan && !generatePlan.isPending) {
    return (
      <div className="scene-empty-state">
        <div className="scene-empty-state__card">
          <div className="scene-empty-state__icon">🎬</div>
          <h2>No scene plan yet</h2>
          <p>Generate a scene plan from the approved script. The system will segment it into scenes, assign shot types, and create start/end frame prompts.</p>
          <button type="button" className="button button--primary" onClick={handleGenerate}>
            Generate scene plan
          </button>
          <Link className="button button--secondary" to={`/app/projects/${projectId}/script`}>
            ← Back to script
          </Link>
        </div>
      </div>
    );
  }

  /* ─── Loading state ───────────────────────────────────────────────────── */
  if (isLoading || generatePlan.isPending) {
    return (
      <div className="page-shell">
        <SceneShimmer />
      </div>
    );
  }

  if (!planSet || !selectedScene) return null;

  /* ─── Main layout ─────────────────────────────────────────────────────── */
  return (
    <div className="page-shell">
      {/* Header */}
      <div className="page-header">
        <div>
          <p className="eyebrow">Scene planner</p>
          <h1 className="page-title">Scene plan</h1>
          <p className="page-description">
            {planSet.scenes.length} scenes · {planSet.totalDurationSec.toFixed(1)}s total
            {planSet.warningsCount > 0 ? ` · ${planSet.warningsCount} warning${planSet.warningsCount > 1 ? "s" : ""}` : ""}
          </p>
        </div>
        <div className="page-actions">
          <Link className="button button--secondary" to={`/app/projects/${projectId}/script`}>
            ← Script
          </Link>
          {!isApproved ? (
            <>
              <button type="button" className="button button--secondary" onClick={handleGenerate} disabled={generatePlan.isPending}>
                Regenerate plan
              </button>
              <button type="button" className="button button--primary" onClick={handleApprove} disabled={approvePlan.isPending}>
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
            <h3 className="section-heading">Timeline</h3>
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
          <div className="surface-card">
            <h3 className="section-heading">Plan status</h3>
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

          <div className="surface-card">
            <h3 className="section-heading">Presets</h3>
            <PresetPicker projectId={projectId} planSet={planSet} />
          </div>

          {selectedScene ? (
            <>
              <div className="surface-card">
                <h3 className="section-heading">Scene {selectedScene.index}</h3>
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
            
            <div className="surface-card">
              <h3 className="section-heading">Prompt Lineage</h3>
              {(!selectedScene.promptHistory || selectedScene.promptHistory.length === 0) ? (
                <p className="body-copy" style={{ fontSize: "12px", color: "var(--color-ink-lighter)" }}>No previous prompt versions logged.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                  {selectedScene.promptHistory.map((h, i) => (
                    <div key={i} style={{ fontSize: "11px", color: "var(--color-ink-lighter)", padding: "8px", background: "var(--color-background)", border: "1px dashed var(--color-border)", borderRadius: "4px", lineHeight: "1.4" }}>
                      {h}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
      </div>
    </div>
  );
}
