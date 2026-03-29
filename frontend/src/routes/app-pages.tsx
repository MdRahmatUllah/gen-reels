import { useEffect, useMemo, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  mockGetBillingData,
  mockGetDashboardData,
  mockGetPresets,
  mockGetProjectBundle,
  mockGetProjects,
  mockGetSettings,
  mockGetTemplates,
} from "../lib/mock-service";
import { useBrief, useUpdateBrief } from "../hooks/use-briefs";

import { useScript, useApproveScript, useGenerateScript } from "../hooks/use-scripts";

import { formatDuration } from "../lib/format";
import {
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
  ProjectBundle,
  ProjectSummary,
  ScenePlan,
  SettingsSection,
} from "../types/domain";

function useProjectData(): { projectId: string; bundle?: ProjectBundle; isLoading: boolean } {
  const params = useParams();
  const projectId = params.projectId ?? "project_aurora_serum";
  const { data, isLoading } = useQuery({
    queryKey: ["project-bundle", projectId],
    queryFn: () => mockGetProjectBundle(projectId),
  });

  return { projectId, bundle: data, isLoading };
}

function LoadingPage() {
  return (
    <PageFrame
      eyebrow="Loading"
      title="Preparing the studio"
      description="Mock project data is loading into the workspace."
      inspector={<div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in shimmer" />}
    >
      <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in shimmer" />
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
        <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">{project.nextMilestone}</p>
        <div className="flex flex-wrap items-center gap-2">
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
    queryFn: mockGetDashboardData,
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
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${focusProject.id}/brief`}>
            Open brief
          </Link>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to={`/app/projects/${focusProject.id}/renders`}>
            Review active render
          </Link>
        </>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Studio alerts">
            <div className="flex flex-col gap-3">
              {data.notifications.map((alert) => (
                <div className="flex gap-3 items-start" key={alert.id}>
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
            <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">{focusProject.hook}</p>
            <div className="flex flex-wrap items-center gap-2">
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
                  <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">{project.stage}</p>
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
    queryFn: mockGetProjects,
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
        <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to={`/app/projects/${data[0]?.id ?? "project_aurora_serum"}/brief`}>
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
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={project.renderStatus} />
              <span>{project.stage}</span>
              <span>{formatDuration(project.durationSec)}</span>
            </div>
            <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">{project.hook}</p>
            <div className="metric-row">
              <MetricCard label="Palette" value={project.palette} detail="Project look system" tone="primary" />
              <MetricCard label="Voice" value={project.voicePreset} detail="Narration preset" tone="neutral" />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${project.id}/script`}>
                Script
              </Link>
              <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to={`/app/projects/${project.id}/brief`}>
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
            <button className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" onClick={handleSave} type="button">
              {updateBrief.isPending ? "Saving…" : "Save brief"}
            </button>
          ) : null}
          <button
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
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
            <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="brief-objective">Objective</label>
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
              <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="brief-hook">Hook</label>
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
              <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="brief-cta">Call to action</label>
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
              <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="brief-audience">Target audience</label>
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
              <label className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1" htmlFor="brief-northstar">Brand north star</label>
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
  const approveScript = useApproveScript(projectId);
  const generateScript = useGenerateScript(projectId);
  const [queuedGeneration, setQueuedGeneration] = useState(false);

  // Get fresh script data from mock-service when available
  const { data: freshScript, isLoading: isScriptLoading } = useScript(projectId);

  useEffect(() => {
    if (freshScript && freshScript.id !== `queued-${projectId}`) {
      setQueuedGeneration(false);
    }
  }, [freshScript, projectId]);

  if (isLoading || isScriptLoading || !bundle) {
    return <LoadingPage />;
  }

  // If no fresh script, show empty generation state
  if (!freshScript && !generateScript.isPending && !queuedGeneration) {
    return (
      <div className="scene-empty-state">
        <div className="scene-empty-state__card">
          <div className="scene-empty-state__icon">📝</div>
          <h2>No script generated yet</h2>
          <p>Generate a script based on your brief and selected idea. The AI will write narration, visual direction, and pacing cues.</p>
          <button 
            type="button" 
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" 
            onClick={() => {
              setQueuedGeneration(true);
              generateScript.mutate();
            }}
          >
            Generate script
          </button>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${projectId}/ideas`}>
            ← Back to ideas
          </Link>
        </div>
      </div>
    );
  }

  if (generateScript.isPending || queuedGeneration || freshScript?.approvalState === "queued") {
    return (
      <PageFrame
        eyebrow="Loading"
        title="Generating script..."
        description="The AI is drafting the script from your selected idea."
        inspector={<div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in shimmer" />}
      >
        <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in shimmer" />
      </PageFrame>
    );
  }

  const scriptData = freshScript;
  if (!scriptData) return null;

  const isApproved = scriptData.approvalState === "approved";

  return (
    <PageFrame
      eyebrow="Script workspace"
      title={`${bundle.project.title} · ${scriptData.versionLabel}`}
      description="Dense but readable script review with clear versioning, per-scene timing, and voice continuity visibility."
      actions={
        <>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${projectId}/ideas`}>
            ← Ideas
          </Link>
          {!isApproved ? (
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
              onClick={() => approveScript.mutate()}
              disabled={approveScript.isPending}
            >
              {approveScript.isPending ? "Approving…" : "Approve script ✓"}
            </button>
          ) : (
            <>
              <span className="approval-badge approval-badge--approved">✓ Approved</span>
              <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to={`/app/projects/${projectId}/scenes`}>
                Segment into scenes →
              </Link>
            </>
          )}
        </>
      }
      inspector={
        <div className="inspector-stack">
          <ProjectInspector project={bundle.project} />
          <SectionCard title="Script facts">
            <div className="inspector-list">
              <div>
                <span>Approval</span>
                <strong className={isApproved ? "text-success" : ""}>{scriptData.approvalState}</strong>
              </div>
              <div>
                <span>Word count</span>
                <strong>{scriptData.totalWords}</strong>
              </div>
              <div>
                <span>Timing</span>
                <strong>{scriptData.readingTimeLabel}</strong>
              </div>
              <div>
                <span>Last edited</span>
                <strong>{scriptData.lastEdited}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard className="surface-card--hero" title="Narration direction" subtitle="Editorial tone with consistent voice parameters across every scene">
        <div className="metric-row">
          <MetricCard label="Voice preset" value={bundle.project.voicePreset} detail="Frozen per render job" tone="primary" />
          <MetricCard label="Approval state" value={scriptData.approvalState} detail={isApproved ? "Script locked — ready for segmentation" : "Approve to proceed"} tone={isApproved ? "success" : "warning"} />
        </div>
      </SectionCard>

      <SectionCard title="Scene-by-scene script table" subtitle="Alternate row surfaces replace table dividers to match the studio design language">
        <ScriptTable bundle={{ ...bundle, script: scriptData }} />
      </SectionCard>

      <SectionCard title="Beat handoff cards" subtitle="Each line carries visual direction and pacing cues into the scene planner">
        <div className="artifact-grid artifact-grid--compact">
          {scriptData.lines.map((line) => (
            <div className="p-4 rounded-xl bg-card border border-border-card animate-rise-in" key={line.id}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">{line.sceneId}</span>
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
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${projectId}/script`}>
            Back to script
          </Link>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to={`/app/projects/${projectId}/renders`}>
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
            <div className="p-4 rounded-xl bg-card border border-border-card animate-rise-in">
              <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Prompt</p>
              <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">{selectedScene.prompt}</p>
            </div>
            <div className="p-4 rounded-xl bg-card border border-border-card animate-rise-in">
              <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Palette + audio cue</p>
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
            <div className="p-4 rounded-xl bg-card border border-border-card animate-rise-in" key={scene.id}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Scene {scene.index}</span>
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


export function PresetsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["presets"],
    queryFn: mockGetPresets,
  });

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Preset library"
      title="Shared systems for look, voice, and motion"
      description="Presets are treated like studio assets: reusable, controlled, and visible to the full production workflow."
      actions={<Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to="/app/templates">Browse templates</Link>}
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
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={preset.category} />
              <span>{preset.status}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {preset.tags.map((tag) => (
                <span className="tag-chip" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
            {preset.look ? <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">{preset.look}</p> : null}
            {preset.voice ? <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">{preset.voice}</p> : null}
            {preset.transitionMode ? <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">Default transition: {preset.transitionMode}</p> : null}
          </SectionCard>
        ))}
      </div>
    </PageFrame>
  );
}

export function TemplatesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: mockGetTemplates,
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
            <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
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
    queryFn: mockGetSettings,
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
            <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
              Shared settings stop drift between projects and make the later API integration predictable.
            </p>
          </SectionCard>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
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
    queryFn: mockGetBillingData,
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
                <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">{invoice.date}</p>
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
