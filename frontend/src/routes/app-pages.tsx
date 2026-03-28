import { useEffect, useMemo, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  defaultProjectId,
  getBillingData,
  getDashboardData,
  getPresets,
  getProjectBundle,
  getProjects,
  getSettingsSections,
  getTemplates,
} from "../lib/mock-api";
import { useBrief, useUpdateBrief } from "../hooks/use-briefs";
import { useProject, useCreateProject } from "../hooks/use-projects";
import { useScript, useGenerateScript, useUpdateScript, useApproveScript } from "../hooks/use-scripts";
import { GenerationStatusIndicator } from "../components/GenerationStatus";
import { formatDuration, formatSignedSeconds } from "../lib/format";
import {
  EmptyState,
  MediaFrame,
  MetricCard,
  PageFrame,
  ProgressBar,
  SectionCard,
  StatusBadge,
  TimelineItem,
} from "../components/ui";
import { useStudioUiStore } from "../state/ui-store";
import type {
  ExportArtifact,
  ProjectBundle,
  ProjectSummary,
  RenderJob,
  RenderStep,
  ScenePlan,
  SettingsSection,
} from "../types/domain";

function useProjectData(): { projectId: string; bundle?: ProjectBundle; isLoading: boolean } {
  const params = useParams();
  const projectId = params.projectId ?? defaultProjectId;
  const { data, isLoading } = useQuery({
    queryKey: ["project-bundle", projectId],
    queryFn: () => getProjectBundle(projectId),
  });

  return { projectId, bundle: data, isLoading };
}

function LoadingPage() {
  return (
    <PageFrame
      eyebrow="Loading"
      title="Preparing the studio"
      description="Mock project data is loading into the workspace."
      inspector={<div className="surface-card shimmer surface-card--loading" />}
    >
      <div className="surface-card shimmer surface-card--loading" />
    </PageFrame>
  );
}

function ProjectInspector({ project }: { project: ProjectSummary }) {
  return (
    <div className="inspector-stack">
      <SectionCard title="Project summary">
        <div className="inspector-list">
          <div>
            <span>Client</span>
            <strong>{project.client}</strong>
          </div>
          <div>
            <span>Stage</span>
            <strong>{project.stage}</strong>
          </div>
          <div>
            <span>Voice preset</span>
            <strong>{project.voicePreset}</strong>
          </div>
          <div>
            <span>Aspect ratio</span>
            <strong>{project.aspectRatio}</strong>
          </div>
          <div>
            <span>Scene count</span>
            <strong>{project.sceneCount}</strong>
          </div>
          <div>
            <span>Duration</span>
            <strong>{formatDuration(project.durationSec)}</strong>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Current milestone">
        <p className="body-copy">{project.nextMilestone}</p>
        <div className="tag-row">
          {project.tags.map((tag) => (
            <span className="tag-chip" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function RenderSummaryCard({ render }: { render: RenderJob }) {
  return (
    <SectionCard
      className="surface-card--hero"
      title={render.label}
      subtitle={`Consistency snapshot ${render.consistencyPackSnapshotId}`}
    >
      <div className="inline-meta">
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

function ScriptTable({ bundle }: { bundle: ProjectBundle }) {
  return (
    <div className="table-shell">
      <table className="studio-table">
        <thead>
          <tr>
            <th>Artifact ID</th>
            <th>Beat</th>
            <th>Narration</th>
            <th>Duration</th>
            <th>Voice</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {bundle.script.lines.map((line) => (
            <tr key={line.id}>
              <td>{line.sceneId}</td>
              <td>{line.beat}</td>
              <td>{line.narration}</td>
              <td>{line.durationSec}s</td>
              <td>{line.voicePacing}</td>
              <td>
                <StatusBadge status={line.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RenderStepTable({ steps }: { steps: RenderStep[] }) {
  return (
    <div className="table-shell">
      <table className="studio-table">
        <thead>
          <tr>
            <th>Artifact ID</th>
            <th>Step</th>
            <th>Status</th>
            <th>Delta</th>
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
                <StatusBadge status={step.status} />
              </td>
              <td>{formatSignedSeconds(step.durationDeltaSec)}</td>
              <td>{step.clipStatus}</td>
              <td>{step.narrationStatus}</td>
              <td>{step.nextAction}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExportCard({ artifact }: { artifact: ExportArtifact }) {
  return (
    <div className="artifact-card">
      <MediaFrame
        label={artifact.name}
        meta={`${artifact.ratio} · ${artifact.format}`}
        gradient={artifact.gradient}
      />
      <div className="artifact-card__meta">
        <div className="inline-meta">
          <StatusBadge status={artifact.status} />
          <span>{formatDuration(artifact.durationSec)}</span>
          <span>{artifact.sizeMb} MB</span>
        </div>
        <strong>{artifact.destination}</strong>
        <p>
          {artifact.subtitles ? "Subtitles on" : "Subtitles off"} ·{" "}
          {artifact.musicBed ? "Music bed on" : "Music bed off"}
        </p>
      </div>
    </div>
  );
}

function SettingsCard({ section }: { section: SettingsSection }) {
  return (
    <SectionCard title={section.title} subtitle={section.description}>
      <div className="inspector-list">
        {section.items.map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            {item.status ? <p>{item.status}</p> : null}
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardData,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  const focusProject = data.focusProject;

  return (
    <PageFrame
      eyebrow="Studio overview"
      title="Digital Director's Desk"
      description="A creator-first production shell that keeps project state, composition quality, and business guardrails visible in one place."
      actions={
        <>
          <Link className="button button--secondary" to={`/app/projects/${focusProject.id}/brief`}>
            Open brief
          </Link>
          <Link className="button button--primary" to={`/app/projects/${focusProject.id}/renders`}>
            Review active render
          </Link>
        </>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Studio alerts">
            <div className="alert-stack">
              {data.notifications.map((alert) => (
                <div className="alert-item" key={alert.id}>
                  <span className={`tone-pill tone-pill--${alert.tone}`} />
                  <div>
                    <strong>{alert.label}</strong>
                    <p>{alert.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Queue pulse">
            <div className="metric-column">
              {data.queueOverview.map((metric) => (
                <MetricCard
                  key={metric.label}
                  label={metric.label}
                  value={metric.value}
                  detail={metric.detail}
                  tone={metric.tone}
                />
              ))}
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard
        className="surface-card--hero"
        title={focusProject.title}
        subtitle={focusProject.objective}
      >
        <div className="hero-grid">
          <div>
            <p className="body-copy">{focusProject.hook}</p>
            <div className="tag-row">
              {focusProject.tags.map((tag) => (
                <span className="tag-chip" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <div className="metric-row">
            <MetricCard label="Palette" value={focusProject.palette} detail="Pinned inside the consistency pack" tone="primary" />
            <MetricCard label="Voice" value={focusProject.voicePreset} detail="Shared across every narration pass" tone="success" />
          </div>
        </div>
      </SectionCard>

      <div className="metric-grid">
        {data.metrics.map((metric) => (
          <MetricCard
            key={metric.label}
            label={metric.label}
            value={metric.value}
            detail={metric.detail}
            tone={metric.tone}
          />
        ))}
      </div>

      <div className="content-grid content-grid--equal">
        <SectionCard title="Composition guardrails" subtitle="Pulled directly from the active render checks">
          <div className="check-list">
            {data.compositionRules.map((rule) => (
              <div className="check-item" key={rule.id}>
                <StatusBadge status={rule.status} />
                <div>
                  <strong>{rule.label}</strong>
                  <p>{rule.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Project pipeline" subtitle="Every route in the documented workflow is represented here">
          <div className="project-list">
            {data.recentProjects.map((project) => (
              <Link className="project-list__item" key={project.id} to={`/app/projects/${project.id}/brief`}>
                <div>
                  <p className="eyebrow">{project.stage}</p>
                  <strong>{project.title}</strong>
                  <p>{project.nextMilestone}</p>
                </div>
                <StatusBadge status={project.renderStatus} />
              </Link>
            ))}
          </div>
        </SectionCard>
      </div>
    </PageFrame>
  );
}

export function ProjectsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: getProjects,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Project library"
      title="All active productions"
      description="Projects keep the same shell shape from brief through exports so the information architecture can survive later phases."
      actions={
        <Link className="button button--primary" to={`/app/projects/${defaultProjectId}/brief`}>
          Open default project
        </Link>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Portfolio view">
            <div className="inspector-list">
              <div>
                <span>Total projects</span>
                <strong>{data.length}</strong>
              </div>
              <div>
                <span>Projects in render</span>
                <strong>{data.filter((project) => project.stage === "renders").length}</strong>
              </div>
              <div>
                <span>Projects in planning</span>
                <strong>{data.filter((project) => project.stage !== "renders").length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <div className="artifact-grid">
        {data.map((project) => (
          <SectionCard key={project.id} title={project.title} subtitle={project.objective}>
            <div className="inline-meta">
              <StatusBadge status={project.renderStatus} />
              <span>{project.stage}</span>
              <span>{formatDuration(project.durationSec)}</span>
            </div>
            <p className="body-copy">{project.hook}</p>
            <div className="metric-row">
              <MetricCard label="Palette" value={project.palette} detail="Project look system" tone="primary" />
              <MetricCard label="Voice" value={project.voicePreset} detail="Narration preset" tone="neutral" />
            </div>
            <div className="card-actions">
              <Link className="button button--secondary" to={`/app/projects/${project.id}/script`}>
                Script
              </Link>
              <Link className="button button--primary" to={`/app/projects/${project.id}/brief`}>
                Open project
              </Link>
            </div>
          </SectionCard>
        ))}
      </div>
    </PageFrame>
  );
}

export function ProjectBriefPage() {
  const { bundle, isLoading, projectId } = useProjectData();
  const navigate = useNavigate();
  const { data: briefData } = useBrief(projectId);
  const updateBrief = useUpdateBrief(projectId);

  const [editing, setEditing] = useState(false);
  const [localBrief, setLocalBrief] = useState({
    objective: "",
    hook: "",
    targetAudience: "",
    callToAction: "",
    brandNorthStar: "",
  });

  // Sync from server data
  useEffect(() => {
    if (briefData) {
      setLocalBrief({
        objective: briefData.objective,
        hook: briefData.hook,
        targetAudience: briefData.targetAudience,
        callToAction: briefData.callToAction,
        brandNorthStar: briefData.brandNorthStar,
      });
    }
  }, [briefData]);

  const handleFieldChange = useCallback((field: string, value: string) => {
    setLocalBrief((prev) => ({ ...prev, [field]: value }));
    setEditing(true);
  }, []);

  const handleSave = useCallback(() => {
    updateBrief.mutate(localBrief);
    setEditing(false);
  }, [localBrief, updateBrief]);

  const handleSaveAndContinue = useCallback(() => {
    updateBrief.mutate(localBrief, {
      onSuccess: () => navigate(`/app/projects/${projectId}/ideas`),
    });
  }, [localBrief, updateBrief, navigate, projectId]);

  if (isLoading || !bundle) {
    return <LoadingPage />;
  }

  const brief = briefData ?? bundle.brief;

  return (
    <PageFrame
      eyebrow="Brief workspace"
      title={bundle.project.title}
      description="The brief sets the production atmosphere, hard constraints, and approval path before any expensive generation begins."
      actions={
        <div style={{ display: "flex", gap: "0.75rem" }}>
          {editing ? (
            <button className="button button--secondary" onClick={handleSave} type="button">
              {updateBrief.isPending ? "Saving…" : "Save brief"}
            </button>
          ) : null}
          <button
            className="button button--primary"
            onClick={handleSaveAndContinue}
            type="button"
          >
            Save & generate ideas →
          </button>
        </div>
      }
      inspector={<ProjectInspector project={bundle.project} />}
    >
      <SectionCard className="surface-card--hero" title="Creative direction" subtitle="Core strategic elements that shape all generation">
        <div className="form-grid">
          <div className="form-field">
            <label className="field-label" htmlFor="brief-objective">Objective</label>
            <textarea
              id="brief-objective"
              className="field-input field-textarea"
              value={localBrief.objective}
              onChange={(e) => handleFieldChange("objective", e.target.value)}
              rows={3}
              placeholder="What should this video achieve?"
            />
          </div>
          <div className="content-grid content-grid--equal">
            <div className="form-field">
              <label className="field-label" htmlFor="brief-hook">Hook</label>
              <textarea
                id="brief-hook"
                className="field-input field-textarea"
                value={localBrief.hook}
                onChange={(e) => handleFieldChange("hook", e.target.value)}
                rows={2}
                placeholder="What stops the scroll?"
              />
            </div>
            <div className="form-field">
              <label className="field-label" htmlFor="brief-cta">Call to action</label>
              <textarea
                id="brief-cta"
                className="field-input field-textarea"
                value={localBrief.callToAction}
                onChange={(e) => handleFieldChange("callToAction", e.target.value)}
                rows={2}
                placeholder="What should viewers do after watching?"
              />
            </div>
          </div>
          <div className="content-grid content-grid--equal">
            <div className="form-field">
              <label className="field-label" htmlFor="brief-audience">Target audience</label>
              <textarea
                id="brief-audience"
                className="field-input field-textarea"
                value={localBrief.targetAudience}
                onChange={(e) => handleFieldChange("targetAudience", e.target.value)}
                rows={2}
                placeholder="Who is this for?"
              />
            </div>
            <div className="form-field">
              <label className="field-label" htmlFor="brief-northstar">Brand north star</label>
              <textarea
                id="brief-northstar"
                className="field-input field-textarea"
                value={localBrief.brandNorthStar}
                onChange={(e) => handleFieldChange("brandNorthStar", e.target.value)}
                rows={2}
                placeholder="Creative tone and positioning"
              />
            </div>
          </div>
        </div>
      </SectionCard>

      <div className="content-grid content-grid--equal">
        <SectionCard title="Guardrails" subtitle="These shape the asset generation prompts and approval review">
          <ul className="bullet-list">
            {brief.guardrails.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard title="Must include" subtitle="Non-negotiable creative and commercial details">
          <ul className="bullet-list">
            {brief.mustInclude.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>
      </div>

      <SectionCard title="Approval sequence" subtitle="Designed to fit the future gated workflow">
        <div className="approval-lane">
          {brief.approvalSteps.map((step, index) => (
            <div className="approval-step" key={step}>
              <span>{index + 1}</span>
              <div>
                <strong>{step}</strong>
                <p>Approval is captured before progressing to the next production stage.</p>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function ScriptPage() {
  const { bundle, isLoading, projectId } = useProjectData();

  if (isLoading || !bundle) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Script workspace"
      title={`${bundle.project.title} · ${bundle.script.versionLabel}`}
      description="Dense but readable script review with clear versioning, per-scene timing, and voice continuity visibility."
      actions={
        <>
          <Link className="button button--secondary" to={`/app/projects/${projectId}/brief`}>
            Back to brief
          </Link>
          <Link className="button button--primary" to={`/app/projects/${projectId}/scenes`}>
            Promote to scenes
          </Link>
        </>
      }
      inspector={
        <div className="inspector-stack">
          <ProjectInspector project={bundle.project} />
          <SectionCard title="Script facts">
            <div className="inspector-list">
              <div>
                <span>Approval</span>
                <strong>{bundle.script.approvalState}</strong>
              </div>
              <div>
                <span>Word count</span>
                <strong>{bundle.script.totalWords}</strong>
              </div>
              <div>
                <span>Timing</span>
                <strong>{bundle.script.readingTimeLabel}</strong>
              </div>
              <div>
                <span>Last edited</span>
                <strong>{bundle.script.lastEdited}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard className="surface-card--hero" title="Narration direction" subtitle="Editorial tone with consistent voice parameters across every scene">
        <div className="metric-row">
          <MetricCard label="Voice preset" value={bundle.project.voicePreset} detail="Frozen per render job" tone="primary" />
          <MetricCard label="Approval state" value={bundle.script.approvalState} detail="Ready to gate renders" tone="success" />
        </div>
      </SectionCard>

      <SectionCard title="Scene-by-scene script table" subtitle="Alternate row surfaces replace table dividers to match the studio design language">
        <ScriptTable bundle={bundle} />
      </SectionCard>

      <SectionCard title="Beat handoff cards" subtitle="Each line carries visual direction and pacing cues into the scene planner">
        <div className="artifact-grid artifact-grid--compact">
          {bundle.script.lines.map((line) => (
            <div className="surface-panel" key={line.id}>
              <div className="inline-meta">
                <span className="eyebrow">{line.sceneId}</span>
                <StatusBadge status={line.status} />
              </div>
              <strong>{line.beat}</strong>
              <p>{line.visualDirection}</p>
              <span>{line.voicePacing}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function ScenesPage() {
  const { bundle, isLoading, projectId } = useProjectData();
  const selectedScenes = useStudioUiStore((state) => state.selectedScenes);
  const setSelectedScene = useStudioUiStore((state) => state.setSelectedScene);

  useEffect(() => {
    if (bundle && !selectedScenes[projectId]) {
      setSelectedScene(projectId, bundle.scenes[0].id);
    }
  }, [bundle, projectId, selectedScenes, setSelectedScene]);

  const selectedScene = useMemo<ScenePlan | undefined>(() => {
    if (!bundle) {
      return undefined;
    }

    return (
      bundle.scenes.find((scene) => scene.id === selectedScenes[projectId]) ??
      bundle.scenes[0]
    );
  }, [bundle, projectId, selectedScenes]);

  if (isLoading || !bundle || !selectedScene) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Scene planner"
      title={`${bundle.project.title} timeline`}
      description="A bespoke timeline list paired with a wide detail canvas so clips, prompts, and continuity notes stay legible during review."
      actions={
        <>
          <Link className="button button--secondary" to={`/app/projects/${projectId}/script`}>
            Back to script
          </Link>
          <Link className="button button--primary" to={`/app/projects/${projectId}/renders`}>
            Open render monitor
          </Link>
        </>
      }
      inspector={
        <div className="inspector-stack">
          <ProjectInspector project={bundle.project} />
          <SectionCard title="Selected scene">
            <div className="inspector-list">
              <div>
                <span>Scene</span>
                <strong>{selectedScene.index}</strong>
              </div>
              <div>
                <span>Continuity score</span>
                <strong>{selectedScene.continuityScore}/100</strong>
              </div>
              <div>
                <span>Keyframe status</span>
                <strong>{selectedScene.keyframeStatus}</strong>
              </div>
              <div>
                <span>Subtitle state</span>
                <strong>{selectedScene.subtitleStatus}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <div className="content-grid content-grid--timeline">
        <SectionCard title="Timeline list" subtitle="Active clip is marked with the left-edge accent from the design brief">
          <div className="timeline-list">
            {bundle.scenes.map((scene) => (
              <TimelineItem
                key={scene.id}
                scene={scene}
                active={scene.id === selectedScene.id}
                onClick={() => setSelectedScene(projectId, scene.id)}
              />
            ))}
          </div>
        </SectionCard>

        <SectionCard title={selectedScene.title} subtitle={selectedScene.beat}>
          <MediaFrame
            label={selectedScene.thumbnailLabel}
            meta={`${selectedScene.shotType} · ${selectedScene.motion}`}
            gradient={selectedScene.gradient}
          />
          <div className="content-grid content-grid--equal">
            <div className="surface-panel">
              <p className="section-heading">Prompt</p>
              <p className="body-copy">{selectedScene.prompt}</p>
            </div>
            <div className="surface-panel">
              <p className="section-heading">Palette + audio cue</p>
              <strong>{selectedScene.palette}</strong>
              <p>{selectedScene.audioCue}</p>
            </div>
          </div>
          <div className="check-list">
            {selectedScene.notes.map((note) => (
              <div className="check-item" key={note}>
                <StatusBadge status={selectedScene.status} />
                <div>
                  <strong>Continuity note</strong>
                  <p>{note}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Transition map" subtitle="Project-level composition intent stays visible while reviewing each scene">
        <div className="artifact-grid artifact-grid--compact">
          {bundle.scenes.map((scene) => (
            <div className="surface-panel" key={scene.id}>
              <div className="inline-meta">
                <span className="eyebrow">Scene {scene.index}</span>
                <StatusBadge status={scene.transitionMode} />
              </div>
              <strong>{scene.title}</strong>
              <p>{scene.audioCue}</p>
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function RendersPage() {
  const { bundle, isLoading } = useProjectData();
  const renderFilter = useStudioUiStore((state) => state.renderFilter);
  const setRenderFilter = useStudioUiStore((state) => state.setRenderFilter);

  if (isLoading || !bundle) {
    return <LoadingPage />;
  }

  const filteredRenders = bundle.renderJobs.filter((render) => {
    if (renderFilter === "all") {
      return true;
    }

    if (renderFilter === "completed") {
      return render.status === "completed";
    }

    return render.status === renderFilter;
  });

  const activeRender = filteredRenders[0] ?? bundle.renderJobs[0];

  return (
    <PageFrame
      eyebrow="Render monitor"
      title={`${bundle.project.title} renders`}
      description="The monitor surfaces job health, composition gates, SSE state, and per-scene timing so users always know the next available action."
      actions={
        <div className="filter-row">
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
      }
      inspector={
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
      }
    >
      <RenderSummaryCard render={activeRender} />

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

        <SectionCard title="Render history" subtitle="Users can inspect previous jobs without losing the current one">
          <div className="project-list">
            {bundle.renderJobs.map((render) => (
              <div className="project-list__item" key={render.id}>
                <div>
                  <p className="eyebrow">{render.createdAt}</p>
                  <strong>{render.label}</strong>
                  <p>{render.nextAction}</p>
                </div>
                <StatusBadge status={render.status} />
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Per-scene execution matrix" subtitle="Retry decisions can stay scoped to the smallest broken unit">
        {activeRender.steps.length > 0 ? (
          <RenderStepTable steps={activeRender.steps} />
        ) : (
          <EmptyState
            title="No active scene steps"
            description="This render already completed, so only the archived metrics remain."
          />
        )}
      </SectionCard>

      <SectionCard title="Event stream" subtitle="A mock view of live render activity surfaced through SSE with polling fallback">
        <div className="event-stream">
          {activeRender.events.map((event) => (
            <div className="event-item" key={event.id}>
              <span className={`tone-pill tone-pill--${event.tone}`} />
              <div>
                <div className="inline-meta">
                  <strong>{event.label}</strong>
                  <span>{event.time}</span>
                </div>
                <p>{event.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function ExportsPage() {
  const { bundle, isLoading } = useProjectData();

  if (isLoading || !bundle) {
    return <LoadingPage />;
  }

  const latestExport = bundle.exports[0];

  return (
    <PageFrame
      eyebrow="Export library"
      title={`${bundle.project.title} exports`}
      description="Final exports expose delivery metadata, loudness outcomes, and channel-specific readiness so release decisions feel operational, not guessy."
      actions={
        <>
          <Link className="button button--secondary" to={`/app/projects/${bundle.project.id}/renders`}>
            Back to renders
          </Link>
          <Link className="button button--primary" to={`/app/projects/${bundle.project.id}/brief`}>
            Review brief context
          </Link>
        </>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Publish checklist">
            <div className="check-list">
              <div className="check-item">
                <StatusBadge status={latestExport.subtitles ? "approved" : "review"} />
                <div>
                  <strong>Subtitle coverage</strong>
                  <p>{latestExport.subtitles ? "Burn-in enabled" : "No subtitles on this export"}</p>
                </div>
              </div>
              <div className="check-item">
                <StatusBadge status={latestExport.musicBed ? "approved" : "review"} />
                <div>
                  <strong>Music continuity</strong>
                  <p>{latestExport.musicBed ? "Music bed delivered with fade" : "No music bed attached"}</p>
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Master metrics">
            <div className="inspector-list">
              <div>
                <span>Integrated loudness</span>
                <strong>{latestExport.integratedLufs} LUFS</strong>
              </div>
              <div>
                <span>True peak</span>
                <strong>{latestExport.truePeak} dBTP</strong>
              </div>
              <div>
                <span>Format</span>
                <strong>{latestExport.format}</strong>
              </div>
              <div>
                <span>Destination</span>
                <strong>{latestExport.destination}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard className="surface-card--hero" title={latestExport.name} subtitle="Latest master output">
        <div className="hero-grid">
          <MediaFrame
            label={latestExport.name}
            meta={`${latestExport.ratio} · ${latestExport.format}`}
            gradient={latestExport.gradient}
            aspect="wide"
          />
          <div className="metric-column">
            <MetricCard label="Duration" value={formatDuration(latestExport.durationSec)} detail="Final export length" tone="primary" />
            <MetricCard label="File size" value={`${latestExport.sizeMb} MB`} detail="Fast-start optimized" tone="neutral" />
            <MetricCard label="Created" value={latestExport.createdAt} detail="Latest delivered artifact" tone="success" />
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Export library" subtitle="Cards stay visual while metadata keeps the operational details close">
        <div className="artifact-grid">
          {bundle.exports.map((artifact) => (
            <ExportCard key={artifact.id} artifact={artifact} />
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Delivery notes" subtitle="The composition worker's output metrics stay visible to the release surface">
        <div className="content-grid content-grid--equal">
          <div className="surface-panel">
            <p className="section-heading">Audio</p>
            <strong>-14 LUFS target achieved</strong>
            <p>The export stays inside short-form platform loudness expectations and the true peak ceiling.</p>
          </div>
          <div className="surface-panel">
            <p className="section-heading">Visual continuity</p>
            <strong>Consistency snapshot locked</strong>
            <p>Scene clips share one consistency pack snapshot and the export profile is uniform end to end.</p>
          </div>
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function PresetsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["presets"],
    queryFn: getPresets,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Preset library"
      title="Shared systems for look, voice, and motion"
      description="Presets are treated like studio assets: reusable, controlled, and visible to the full production workflow."
      actions={<Link className="button button--primary" to="/app/templates">Browse templates</Link>}
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Library facts">
            <div className="inspector-list">
              <div>
                <span>Total presets</span>
                <strong>{data.length}</strong>
              </div>
              <div>
                <span>Visual systems</span>
                <strong>{data.filter((preset) => preset.category === "visual").length}</strong>
              </div>
              <div>
                <span>Voice systems</span>
                <strong>{data.filter((preset) => preset.category === "voice").length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <div className="artifact-grid">
        {data.map((preset) => (
          <SectionCard key={preset.id} title={preset.name} subtitle={preset.description}>
            <div className="inline-meta">
              <StatusBadge status={preset.category} />
              <span>{preset.status}</span>
            </div>
            <div className="tag-row">
              {preset.tags.map((tag) => (
                <span className="tag-chip" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
            {preset.look ? <p className="body-copy">{preset.look}</p> : null}
            {preset.voice ? <p className="body-copy">{preset.voice}</p> : null}
            {preset.transitionMode ? <p className="body-copy">Default transition: {preset.transitionMode}</p> : null}
          </SectionCard>
        ))}
      </div>
    </PageFrame>
  );
}

export function TemplatesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: getTemplates,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Templates"
      title="Production starters"
      description="Template concepts make the product feel complete early, while still leaving room for future backend-driven generation flows."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Template intent">
            <p className="body-copy">
              Each template packages a scene count, duration band, and visual tone so project creation can stay lightweight.
            </p>
          </SectionCard>
        </div>
      }
    >
      <div className="artifact-grid">
        {data.map((template) => (
          <SectionCard key={template.id} title={template.name} subtitle={template.description}>
            <div className="metric-row">
              <MetricCard label="Duration band" value={template.duration} detail="Recommended export length" tone="primary" />
              <MetricCard label="Scenes" value={String(template.scenes)} detail={template.style} tone="neutral" />
            </div>
          </SectionCard>
        ))}
      </div>
    </PageFrame>
  );
}

export function SettingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettingsSections,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Settings"
      title="Workspace operating rules"
      description="These screens are mock-driven, but they already reflect the documented boundaries between workflow defaults, approvals, and business controls."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Why this matters">
            <p className="body-copy">
              Shared settings stop drift between projects and make the later API integration predictable.
            </p>
          </SectionCard>
        </div>
      }
    >
      <div className="stack-gap">
        {data.map((section) => (
          <SettingsCard key={section.title} section={section} />
        ))}
      </div>
    </PageFrame>
  );
}

export function BillingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["billing"],
    queryFn: getBillingData,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Billing"
      title="Metered production economics"
      description="The billing view reflects the product direction in the docs: generation is a metered product, not an unlimited feature."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Plan status">
            <div className="inspector-list">
              <div>
                <span>Plan</span>
                <strong>{data.planName}</strong>
              </div>
              <div>
                <span>Cycle</span>
                <strong>{data.cycleLabel}</strong>
              </div>
              <div>
                <span>Projected spend</span>
                <strong>{data.projectedSpend}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard className="surface-card--hero" title="Credit position" subtitle={data.cycleLabel}>
        <ProgressBar
          value={(data.creditsRemaining / data.creditsTotal) * 100}
          label="Credits remaining"
          detail={`${data.creditsRemaining} of ${data.creditsTotal} credits left`}
        />
      </SectionCard>

      <SectionCard title="Usage breakdown" subtitle="Modeled around the platform's expensive pipeline steps">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Usage</th>
                <th>Unit cost</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {data.usageBreakdown.map((row) => (
                <tr key={row.category}>
                  <td>{row.category}</td>
                  <td>{row.usage}</td>
                  <td>{row.unitCost}</td>
                  <td>{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard title="Invoices and reviews" subtitle="A mock ledger surface for subscription and overage visibility">
        <div className="project-list">
          {data.invoices.map((invoice) => (
            <div className="project-list__item" key={invoice.id}>
              <div>
                <p className="eyebrow">{invoice.date}</p>
                <strong>{invoice.label}</strong>
                <p>{invoice.amount}</p>
              </div>
              <StatusBadge status={invoice.status} />
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}
