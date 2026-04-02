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
  mockGetAllVideos,
} from "../lib/mock-service";
import { useBrief, useUpdateBrief } from "../hooks/use-briefs";
import { useQuickCreateStatus } from "../hooks/use-projects";

import { useScript, useApproveScript, useGenerateScript } from "../hooks/use-scripts";
import { QuickCreateProjectModal } from "../features/projects/QuickCreateProjectModal";
import { QuickStartStatusBanner } from "../features/projects/quick-start";

import { formatDuration, relativeTime } from "../lib/format";
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
  DashboardVideo,
  ProjectBundle,
  ProjectSummary,
  QuickCreateStatus,
  ScenePlan,
  ScriptLine,
  SettingsSection,
} from "../types/domain";

function useProjectData(): { projectId: string; bundle?: ProjectBundle; isLoading: boolean } {
  const params = useParams();
  const projectId = params.projectId ?? "project_aurora_serum";
  const { data, isLoading } = useQuery({
    queryKey: ["project-bundle", projectId],
    queryFn: () => mockGetProjectBundle(projectId),
    refetchInterval: 2000,
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

function activeQuickStart(status: QuickCreateStatus | undefined): QuickCreateStatus | null {
  return status && (status.isActive || status.hasFailed) ? status : null;
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



/* ─── Script Page Icons ───────────────────────────────────────────────────── */
function ScriptEyeIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function ScriptMicIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
      <path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" />
    </svg>
  );
}

function ScriptCheckIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function ScriptArrowIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function ScriptSparklesIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
    </svg>
  );
}

function ScriptDocIcon({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  );
}

/* ─── Script Line Card ────────────────────────────────────────────────────── */
function ScriptLineCard({ line, index }: { line: ScriptLine; index: number }) {
  return (
    <div className="script-line" style={{ animationDelay: `${index * 50}ms` }}>
      <span className="script-line__number">{index + 1}</span>
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <span className="text-[0.6875rem] tracking-widest uppercase font-bold text-muted">{line.sceneId}</span>
            <strong className="font-heading text-[0.95rem] font-bold text-primary leading-snug">{line.beat}</strong>
          </div>
          <div className="flex items-center gap-2">
            <span className="duration-badge">{line.durationSec}s</span>
            <StatusBadge status={line.status} />
          </div>
        </div>
        <p className="script-line__narration">{line.narration}</p>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mt-1 pt-2 border-t border-border-subtle">
          {line.visualDirection ? (
            <span className="script-line__direction">
              <ScriptEyeIcon /> {line.visualDirection}
            </span>
          ) : null}
          {line.voicePacing ? (
            <span className="script-line__direction">
              <ScriptMicIcon /> {line.voicePacing}
            </span>
          ) : null}
        </div>
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

function formatVideoDuration(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s < 10 ? "0" : ""}${s}s`;
}

function DashboardVideoCard({ video }: { video: DashboardVideo }) {
  return (
    <div className="dash-video-card animate-rise-in">
      <div className="dash-video-card__media">
        {video.downloadUrl ? (
          <video
            src={video.downloadUrl}
            controls
            playsInline
            className="w-full"
            style={{ maxHeight: "180px", objectFit: "cover" }}
          />
        ) : (
          <div
            className="flex items-end p-4"
            style={{ background: video.gradient, minHeight: "120px" }}
          >
            <div className="relative z-10 flex flex-col gap-0.5">
              <span className="text-[0.6rem] font-bold uppercase tracking-widest text-white/60">{video.format}</span>
              <span className="text-xs font-semibold text-white">{video.name}</span>
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          </div>
        )}
      </div>
      <div className="dash-video-card__body">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <strong className="text-sm text-primary leading-snug line-clamp-1 block">{video.name}</strong>
            <p className="text-xs text-muted mt-0.5">{video.projectTitle}</p>
          </div>
          <StatusBadge status={video.status} />
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <span className="inline-flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {formatVideoDuration(video.durationSec)}
          </span>
          <span>{video.format}</span>
        </div>
      </div>
      <div className="dash-video-card__actions">
        <Link className="btn-ghost !min-h-[1.8rem] !px-3 !py-0.5 !text-xs flex-1 text-center" to={`/app/projects/${video.projectId}/exports`}>
          Exports
        </Link>
        {video.downloadUrl && (
          <a href={video.downloadUrl} download={video.name} className="btn-primary !min-h-[1.8rem] !px-3 !py-0.5 !text-xs flex-1 text-center">
            Download
          </a>
        )}
      </div>
    </div>
  );
}

function DashCheckIcon({ status }: { status: string }) {
  const isPassing = status === "pass" || status === "healthy";
  return (
    <div className={`dash-check__icon ${isPassing ? "bg-success-bg text-success" : "bg-warning-bg text-warning"}`}>
      {isPassing ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      )}
    </div>
  );
}

function DashProjectRow({ project }: { project: ProjectSummary }) {
  const gradient = stageGradients[project.stage] ?? stageGradients.brief;
  const currentStage = WORKFLOW_STAGES.find((s) => s.key === project.stage);
  return (
    <Link to={`/app/projects/${project.id}/brief`} className="dash-project-row animate-rise-in group">
      <span className="inline-block h-9 w-1 rounded-full shrink-0" style={{ background: gradient }} />
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[0.65rem] font-bold uppercase tracking-widest text-muted">{project.client}</span>
        </div>
        <h4 className="text-sm font-semibold text-primary leading-snug truncate">{project.title}</h4>
      </div>
      <div className="hidden sm:flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-[0.7rem] font-semibold capitalize" style={{ color: "var(--accent)" }}>
          <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: gradient }} />
          {currentStage?.label}
        </span>
      </div>
      <StatusBadge status={project.renderStatus} />
      <svg className="text-muted group-hover:text-primary transition-colors shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
    </Link>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: mockGetDashboardData,
  });
  const [isQuickCreateOpen, setQuickCreateOpen] = useState(false);

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  const fp = data.focusProject;
  const fpGradient = stageGradients[fp.stage] ?? stageGradients.brief;
  const fpStage = WORKFLOW_STAGES.find((s) => s.key === fp.stage);
  const creditsMetric = data.metrics.find((m) => m.label.toLowerCase().includes("credit"));
  const projectsMetric = data.metrics.find((m) => m.label.toLowerCase().includes("project"));
  const queueMetric = data.metrics.find((m) => m.label.toLowerCase().includes("queue"));

  return (
    <PageFrame
      eyebrow="Dashboard"
      title="Welcome back"
      description="Here's an overview of your workspace activity, active projects, and production pipeline."
      actions={
        <>
          <button type="button" className="btn-primary" onClick={() => setQuickCreateOpen(true)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            New Project
          </button>
          <Link className="btn-ghost" to="/app/projects">
            View Projects
          </Link>
        </>
      }
      inspector={
        <div className="inspector-stack">
          {/* Credit usage */}
          <SectionCard title="Credits">
            <div className="flex flex-col gap-3">
              <ProgressBar
                value={creditsMetric ? (Number(creditsMetric.value) / 1200) * 100 : 70}
                label="Credits remaining"
                detail={creditsMetric ? `${creditsMetric.value} ${creditsMetric.detail}` : undefined}
              />
            </div>
          </SectionCard>

          {/* Quick links */}
          <SectionCard title="Quick Actions">
            <div className="flex flex-col gap-2">
              <Link to="/app/projects" className="dash-quick-link">
                <span className="dash-quick-link__icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
                </span>
                All Projects
              </Link>
              <Link to="/app/videos" className="dash-quick-link">
                <span className="dash-quick-link__icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                </span>
                Video Library
              </Link>
              <Link to="/app/templates" className="dash-quick-link">
                <span className="dash-quick-link__icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><circle cx="17.5" cy="17.5" r="3.5"/></svg>
                </span>
                Templates
              </Link>
              <Link to="/app/presets" className="dash-quick-link">
                <span className="dash-quick-link__icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </span>
                Presets
              </Link>
            </div>
          </SectionCard>

          {/* Queue pulse */}
          <SectionCard title="Pipeline Status">
            <div className="flex flex-col gap-2">
              {data.queueOverview.map((q) => (
                <div key={q.label} className="flex items-center justify-between rounded-lg bg-glass px-3 py-2">
                  <span className="text-xs text-secondary">{q.label}</span>
                  <strong className="text-sm font-bold text-primary">{q.value}</strong>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      }
    >
      {/* ── Quick Stats ─────────────────────────────────────────────────── */}
      <div className="dash-stats">
        <div className="dash-stat">
          <div className="dash-stat__icon bg-primary-bg text-accent">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
          </div>
          <div className="flex flex-col">
            <span className="dash-stat__value">{projectsMetric?.value ?? data.recentProjects.length}</span>
            <span className="dash-stat__label">Active Projects</span>
          </div>
        </div>
        <div className="dash-stat">
          <div className="dash-stat__icon bg-success-bg text-success">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          </div>
          <div className="flex flex-col">
            <span className="dash-stat__value">{creditsMetric?.value ?? "—"}</span>
            <span className="dash-stat__label">Credits Left</span>
          </div>
        </div>
        <div className="dash-stat">
          <div className="dash-stat__icon bg-warning-bg text-warning">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6" r="1"/><circle cx="3" cy="12" r="1"/><circle cx="3" cy="18" r="1"/></svg>
          </div>
          <div className="flex flex-col">
            <span className="dash-stat__value">{queueMetric?.value ?? "0"}</span>
            <span className="dash-stat__label">Queue Depth</span>
          </div>
        </div>
        <div className="dash-stat">
          <div className="dash-stat__icon" style={{ background: "rgba(139,92,246,0.12)", color: "#8b5cf6" }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><path d="M8 21h8M12 17v4"/></svg>
          </div>
          <div className="flex flex-col">
            <span className="dash-stat__value">{data.recentVideos.length}</span>
            <span className="dash-stat__label">Videos Created</span>
          </div>
        </div>
      </div>

      {/* ── Focus Project Hero ──────────────────────────────────────────── */}
      <div className="dash-hero animate-rise-in">
        <div className="dash-hero__gradient" style={{ background: fpGradient }} />
        <div className="dash-hero__content">
          <div className="dash-hero__top">
            <div className="dash-hero__info">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[0.65rem] font-bold uppercase tracking-widest text-muted">{fp.client}</span>
                <span className="inline-flex items-center gap-1.5 text-[0.72rem] font-semibold capitalize" style={{ color: "var(--accent)" }}>
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: fpGradient }} />
                  {fpStage?.label ?? fp.stage}
                </span>
                <StatusBadge status={fp.renderStatus} />
              </div>
              <h3 className="font-heading text-xl md:text-2xl font-bold text-primary leading-snug">{fp.title}</h3>
              {fp.hook && <p className="text-sm text-secondary leading-relaxed max-w-[56ch]">{fp.hook}</p>}
              {fp.objective && !fp.hook && <p className="text-sm text-secondary leading-relaxed max-w-[56ch]">{fp.objective}</p>}
              <div className="flex flex-wrap items-center gap-2 mt-1">
                {fp.tags.map((tag) => (
                  <span className="inline-flex items-center rounded-md bg-glass px-2 py-0.5 text-[0.7rem] font-medium text-muted" key={tag}>{tag}</span>
                ))}
              </div>
            </div>
            <div className="dash-hero__aside">
              <div className="dash-hero__mini-stat">
                <svg className="text-muted shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><path d="M8 21h8M12 17v4"/></svg>
                <span className="text-xs text-secondary">{fp.sceneCount} scenes</span>
                <span className="text-xs text-muted mx-1">·</span>
                <span className="text-xs text-secondary">{formatDuration(fp.durationSec)}</span>
              </div>
              <div className="dash-hero__mini-stat">
                <svg className="text-muted shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                <span className="text-xs text-secondary truncate">{fp.palette}</span>
              </div>
              <div className="dash-hero__mini-stat">
                <svg className="text-muted shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                <span className="text-xs text-secondary truncate">{fp.voicePreset}</span>
              </div>
              <Link className="btn-primary !text-xs mt-1" to={`/app/projects/${fp.id}/${fp.stage}`}>
                Continue working
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </Link>
            </div>
          </div>
          <p className="text-xs text-muted">
            Next: {fp.nextMilestone}
          </p>
        </div>
      </div>

      {/* ── Two-column: Projects + Quality Checks ──────────────────────── */}
      <div className="content-grid content-grid--equal">
        <SectionCard title="Active Projects" subtitle={`${data.recentProjects.length} project${data.recentProjects.length !== 1 ? "s" : ""} in your workspace`}>
          {data.recentProjects.length > 0 ? (
            <div className="flex flex-col gap-2.5">
              {data.recentProjects.map((project) => (
                <DashProjectRow key={project.id} project={project} />
              ))}
              <div className="flex justify-end mt-1">
                <Link className="text-xs font-semibold text-accent hover:underline" to="/app/projects">
                  View all projects →
                </Link>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-glass">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>
              </div>
              <p className="text-sm text-secondary">No projects yet. Create your first one to get started.</p>
              <button type="button" className="btn-primary !text-xs" onClick={() => setQuickCreateOpen(true)}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                New Project
              </button>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Quality Checks" subtitle="Production guardrails for your active renders">
          <div className="flex flex-col gap-2.5">
            {data.compositionRules.map((rule) => (
              <div className="dash-check" key={rule.id}>
                <DashCheckIcon status={rule.status} />
                <div className="flex flex-col min-w-0">
                  <strong className="text-sm font-semibold text-primary">{rule.label}</strong>
                  <p className="text-xs text-secondary mt-0.5">{rule.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      {/* ── Recent Videos ───────────────────────────────────────────────── */}
      <SectionCard
        title="Recent Videos"
        subtitle={data.recentVideos.length > 0 ? "Latest exports across your workspace" : undefined}
      >
        {data.recentVideos.length > 0 ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {data.recentVideos.map((video) => (
                <DashboardVideoCard key={video.id} video={video} />
              ))}
            </div>
            <div className="flex justify-end mt-2">
              <Link className="text-xs font-semibold text-accent hover:underline" to="/app/videos">
                View all videos →
              </Link>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-4 py-10 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-glass">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </div>
            <div className="flex flex-col gap-1">
              <h4 className="font-heading text-base font-bold text-primary">No videos yet</h4>
              <p className="text-sm text-secondary max-w-sm">Complete a render pipeline in any project to see your generated videos here.</p>
            </div>
            <Link className="btn-primary !text-xs" to={`/app/projects/${fp.id}/renders`}>
              Go to renders
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </Link>
          </div>
        )}
      </SectionCard>

      <QuickCreateProjectModal
        open={isQuickCreateOpen}
        onClose={() => setQuickCreateOpen(false)}
      />
    </PageFrame>
  );
}

function VideoLibraryCard({ video }: { video: DashboardVideo }) {
  return (
    <div className="dash-video-card animate-rise-in group">
      <div className="dash-video-card__media relative">
        {video.downloadUrl ? (
          <video
            src={video.downloadUrl}
            controls
            playsInline
            className="w-full"
            style={{ maxHeight: "200px", objectFit: "cover" }}
          />
        ) : (
          <div
            className="relative flex items-end p-4"
            style={{ background: video.gradient, minHeight: "140px" }}
          >
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
            <div className="relative z-10 flex items-center gap-2">
              <svg className="text-white/70" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              <span className="text-xs font-semibold text-white">{video.name}</span>
            </div>
          </div>
        )}
      </div>
      <div className="dash-video-card__body">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <strong className="text-sm text-primary leading-snug line-clamp-1 block">{video.name}</strong>
            <p className="text-xs text-muted mt-0.5 truncate">{video.projectTitle}</p>
          </div>
          <StatusBadge status={video.status} />
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <span className="inline-flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {formatVideoDuration(video.durationSec)}
          </span>
          <span>{video.format}</span>
          <span className="ml-auto">{relativeTime(video.createdAt)}</span>
        </div>
      </div>
      <div className="dash-video-card__actions">
        <Link className="btn-ghost !min-h-[1.8rem] !px-3 !py-0.5 !text-xs flex-1 text-center" to={`/app/projects/${video.projectId}/exports`}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
          Project
        </Link>
        {video.downloadUrl ? (
          <a href={video.downloadUrl} download={video.name} className="btn-primary !min-h-[1.8rem] !px-3 !py-0.5 !text-xs flex-1 text-center">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Download
          </a>
        ) : (
          <span className="btn-ghost !min-h-[1.8rem] !px-3 !py-0.5 !text-xs flex-1 text-center opacity-50 pointer-events-none">
            Processing...
          </span>
        )}
      </div>
    </div>
  );
}

function VideoListRow({ video }: { video: DashboardVideo }) {
  return (
    <div className="group flex items-center gap-4 rounded-xl border border-border-card bg-card px-5 py-3.5 transition-all duration-200 hover:border-border-active hover:shadow-md hover:-translate-y-px animate-rise-in">
      {/* Thumbnail */}
      <div
        className="relative h-12 w-20 shrink-0 rounded-lg overflow-hidden flex items-center justify-center"
        style={{ background: video.gradient }}
      >
        <svg className="text-white/80" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      </div>

      {/* Info */}
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <h4 className="text-sm font-semibold text-primary leading-snug truncate">{video.name}</h4>
        <p className="text-xs text-muted truncate">{video.projectTitle}</p>
      </div>

      {/* Meta */}
      <div className="hidden md:flex items-center gap-4 text-xs text-muted shrink-0">
        <span className="inline-flex items-center gap-1">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {formatVideoDuration(video.durationSec)}
        </span>
        <span>{video.format}</span>
        <span>{relativeTime(video.createdAt)}</span>
      </div>

      <StatusBadge status={video.status} />

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <Link className="btn-ghost !min-h-[2rem] !px-3 !py-1 !text-xs" to={`/app/projects/${video.projectId}/exports`}>
          Project
        </Link>
        {video.downloadUrl ? (
          <a href={video.downloadUrl} download={video.name} className="btn-primary !min-h-[2rem] !px-3 !py-1 !text-xs">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Download
          </a>
        ) : (
          <span className="text-xs text-muted italic">Processing</span>
        )}
      </div>
    </div>
  );
}

export function VideosPage() {
  const { data: videos, isLoading } = useQuery({
    queryKey: ["all-videos"],
    queryFn: mockGetAllVideos,
  });
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const filteredVideos = useMemo(() => {
    if (!videos) return [];
    let list = [...videos];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          v.projectTitle.toLowerCase().includes(q) ||
          v.format.toLowerCase().includes(q),
      );
    }
    if (statusFilter) {
      list = list.filter((v) => v.status === statusFilter);
    }
    return list;
  }, [videos, search, statusFilter]);

  if (isLoading || !videos) {
    return <LoadingPage />;
  }

  const readyCount = videos.filter((v) => v.status === "ready").length;
  const processingCount = videos.filter((v) => v.status === "processing").length;
  const totalDurationSec = videos.reduce((sum, v) => sum + v.durationSec, 0);
  const uniqueProjects = new Set(videos.map((v) => v.projectId)).size;

  return (
    <PageFrame
      eyebrow="Videos"
      title="Your Videos"
      description="Browse, search, and download all generated videos across your workspace."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Library Stats">
            <div className="flex flex-col gap-3">
              <div className="stat-card">
                <div className="stat-card__icon" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{videos.length}</span>
                  <span className="stat-card__label">Total videos</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon bg-success-bg text-success">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{readyCount}</span>
                  <span className="stat-card__label">Ready to download</span>
                </div>
              </div>
              {processingCount > 0 && (
                <div className="stat-card">
                  <div className="stat-card__icon bg-warning-bg text-warning">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                  </div>
                  <div className="flex flex-col">
                    <span className="stat-card__value">{processingCount}</span>
                    <span className="stat-card__label">Processing</span>
                  </div>
                </div>
              )}
              <div className="stat-card">
                <div className="stat-card__icon bg-primary-bg text-accent">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{formatVideoDuration(totalDurationSec)}</span>
                  <span className="stat-card__label">Total duration</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon" style={{ background: "rgba(236,72,153,0.12)", color: "#ec4899" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{uniqueProjects}</span>
                  <span className="stat-card__label">From projects</span>
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      {/* Toolbar */}
      <div className="projects-toolbar">
        <div className="relative flex-1 min-w-0">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input
            className="projects-search !pl-10"
            placeholder="Search by name, project, or format..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search videos"
          />
        </div>

        <div className="stage-filters">
          <button
            type="button"
            className={statusFilter === null ? "chip-button chip-button--active" : "chip-button"}
            onClick={() => setStatusFilter(null)}
          >
            All ({videos.length})
          </button>
          {readyCount > 0 && (
            <button
              type="button"
              className={statusFilter === "ready" ? "chip-button chip-button--active" : "chip-button"}
              onClick={() => setStatusFilter(statusFilter === "ready" ? null : "ready")}
            >
              Ready ({readyCount})
            </button>
          )}
          {processingCount > 0 && (
            <button
              type="button"
              className={statusFilter === "processing" ? "chip-button chip-button--active" : "chip-button"}
              onClick={() => setStatusFilter(statusFilter === "processing" ? null : "processing")}
            >
              Processing ({processingCount})
            </button>
          )}
        </div>

        <div className="flex items-center rounded-lg border border-border-subtle bg-glass p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("grid")}
            className={`inline-flex items-center justify-center h-8 w-8 rounded-md transition-all duration-200 ${viewMode === "grid" ? "bg-primary-bg text-primary shadow-sm" : "text-muted hover:text-primary"}`}
            aria-label="Grid view"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={`inline-flex items-center justify-center h-8 w-8 rounded-md transition-all duration-200 ${viewMode === "list" ? "bg-primary-bg text-primary shadow-sm" : "text-muted hover:text-primary"}`}
            aria-label="List view"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          </button>
        </div>
      </div>

      {/* Video grid / list */}
      {filteredVideos.length > 0 ? (
        viewMode === "grid" ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 animate-fade-in-up">
            {filteredVideos.map((video) => (
              <VideoLibraryCard key={video.id} video={video} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-3 animate-fade-in-up">
            {filteredVideos.map((video) => (
              <VideoListRow key={video.id} video={video} />
            ))}
          </div>
        )
      ) : search || statusFilter ? (
        <div className="projects-empty">
          <div className="projects-empty__icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </div>
          <h3 className="font-heading text-lg font-bold text-primary">No matching videos</h3>
          <p className="text-secondary max-w-sm text-sm">Try adjusting your search or clearing the filters.</p>
          <button type="button" className="btn-ghost" onClick={() => { setSearch(""); setStatusFilter(null); }}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="projects-empty">
          <div className="projects-empty__icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          </div>
          <h3 className="font-heading text-xl font-bold text-primary">No videos yet</h3>
          <p className="text-secondary max-w-md text-sm leading-relaxed">
            Your generated videos will appear here. Complete a render pipeline in any project to create your first video export.
          </p>
          <Link className="btn-primary" to="/app/projects">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
            Browse Projects
          </Link>
        </div>
      )}
    </PageFrame>
  );
}

const WORKFLOW_STAGES: Array<{ key: ProjectSummary["stage"]; label: string }> = [
  { key: "brief", label: "Brief" },
  { key: "ideas", label: "Ideas" },
  { key: "script", label: "Script" },
  { key: "scenes", label: "Scenes" },
  { key: "frames", label: "Frames" },
  { key: "renders", label: "Renders" },
  { key: "exports", label: "Exports" },
];

const stageGradients: Record<string, string> = {
  brief:   "linear-gradient(135deg, #6366f1, #8b5cf6)",
  ideas:   "linear-gradient(135deg, #f59e0b, #f97316)",
  script:  "linear-gradient(135deg, #10b981, #059669)",
  scenes:  "linear-gradient(135deg, #3b82f6, #2563eb)",
  frames:  "linear-gradient(135deg, #8b5cf6, #a855f7)",
  renders: "linear-gradient(135deg, #ec4899, #f43f5e)",
  exports: "linear-gradient(135deg, #14b8a6, #06b6d4)",
};

function stageIndex(stage: string): number {
  return WORKFLOW_STAGES.findIndex((s) => s.key === stage);
}

function ProjectWorkflowDots({ stage }: { stage: string }) {
  const active = stageIndex(stage);
  return (
    <div className="project-card__progress" title={`Current stage: ${stage}`}>
      {WORKFLOW_STAGES.map((s, i) => (
        <div
          key={s.key}
          className={`project-card__progress-dot ${
            i < active
              ? "project-card__progress-dot--done"
              : i === active
                ? "project-card__progress-dot--active"
                : "project-card__progress-dot--pending"
          }`}
        />
      ))}
    </div>
  );
}

function ProjectCard({ project }: { project: ProjectSummary }) {
  const gradient = stageGradients[project.stage] ?? stageGradients.brief;
  const currentStage = WORKFLOW_STAGES.find((s) => s.key === project.stage);

  return (
    <div className="project-card group">
      <div className="project-card__accent" style={{ background: gradient }} />
      <div className="project-card__body">
        <div className="project-card__header">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="project-card__client">{project.client}</span>
            <h3 className="project-card__title">{project.title}</h3>
          </div>
          <StatusBadge status={project.renderStatus} />
        </div>

        {project.hook && (
          <p className="project-card__hook">{project.hook}</p>
        )}
        {!project.hook && project.objective && (
          <p className="project-card__hook">{project.objective}</p>
        )}

        <ProjectWorkflowDots stage={project.stage} />

        <div className="project-card__stats">
          <span className="project-card__stat">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><path d="M8 21h8M12 17v4"/></svg>
            {project.sceneCount} {project.sceneCount === 1 ? "scene" : "scenes"}
          </span>
          {project.durationSec > 0 && (
            <span className="project-card__stat">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {formatDuration(project.durationSec)}
            </span>
          )}
          <span className="project-card__stat">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            {relativeTime(project.updatedAt)}
          </span>
        </div>

        {project.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {project.tags.slice(0, 3).map((tag) => (
              <span className="inline-flex items-center rounded-md bg-glass px-2 py-0.5 text-[0.68rem] font-medium text-muted" key={tag}>
                {tag}
              </span>
            ))}
            {project.tags.length > 3 && (
              <span className="inline-flex items-center rounded-md bg-glass px-2 py-0.5 text-[0.68rem] font-medium text-muted">
                +{project.tags.length - 3}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="project-card__footer">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent capitalize">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: gradient }} />
          {currentStage?.label ?? project.stage}
        </span>
        <div className="project-card__actions">
          <Link
            className="btn-ghost !min-h-[2rem] !px-3 !py-1 !text-xs"
            to={`/app/projects/${project.id}/${project.stage}`}
          >
            Continue
          </Link>
          <Link
            className="btn-primary !min-h-[2rem] !px-3 !py-1 !text-xs"
            to={`/app/projects/${project.id}/brief`}
          >
            Open
          </Link>
        </div>
      </div>
    </div>
  );
}

export function ProjectsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: mockGetProjects,
  });
  const [isQuickCreateOpen, setQuickCreateOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const filteredProjects = useMemo(() => {
    if (!data) return [];
    let list = [...data];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.client.toLowerCase().includes(q) ||
          p.hook.toLowerCase().includes(q) ||
          p.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    if (stageFilter) {
      list = list.filter((p) => p.stage === stageFilter);
    }
    return list.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    );
  }, [data, search, stageFilter]);

  const stageCounts = useMemo(() => {
    if (!data) return {};
    const counts: Record<string, number> = {};
    for (const p of data) {
      counts[p.stage] = (counts[p.stage] || 0) + 1;
    }
    return counts;
  }, [data]);

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  const totalProjects = data.length;
  const inRender = data.filter((p) => p.stage === "renders").length;
  const totalScenes = data.reduce((sum, p) => sum + p.sceneCount, 0);

  return (
    <PageFrame
      eyebrow="Projects"
      title="Your Projects"
      description="Manage and track all your video productions from brief to final export."
      actions={
        <button
          type="button"
          className="btn-primary"
          onClick={() => setQuickCreateOpen(true)}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Project
        </button>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Overview">
            <div className="flex flex-col gap-3">
              <div className="stat-card">
                <div className="stat-card__icon bg-primary-bg text-accent">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{totalProjects}</span>
                  <span className="stat-card__label">Total projects</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon bg-success-bg text-success">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{inRender}</span>
                  <span className="stat-card__label">Rendering</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon bg-warning-bg text-warning">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><path d="M8 21h8M12 17v4"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{totalScenes}</span>
                  <span className="stat-card__label">Total scenes</span>
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="By Stage">
            <div className="flex flex-col gap-2">
              {WORKFLOW_STAGES.map((s) => {
                const count = stageCounts[s.key] || 0;
                const pct = totalProjects > 0 ? (count / totalProjects) * 100 : 0;
                return (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => setStageFilter(stageFilter === s.key ? null : s.key)}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2 text-xs transition-all duration-200 cursor-pointer ${
                      stageFilter === s.key
                        ? "bg-primary-bg border border-border-active text-primary font-semibold"
                        : "bg-transparent hover:bg-glass border border-transparent text-secondary hover:text-primary"
                    }`}
                  >
                    <span className="inline-block h-2 w-2 rounded-full shrink-0" style={{ background: stageGradients[s.key] }} />
                    <span className="flex-1 text-left">{s.label}</span>
                    <span className="font-bold text-primary">{count}</span>
                    <div className="w-12 h-1 rounded-full bg-border-subtle overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: stageGradients[s.key] }} />
                    </div>
                  </button>
                );
              })}
            </div>
          </SectionCard>
        </div>
      }
    >
      {/* Toolbar: search + filter + view toggle */}
      <div className="projects-toolbar">
        <div className="relative flex-1 min-w-0">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input
            className="projects-search !pl-10"
            placeholder="Search by title, client, or tag..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search projects"
          />
        </div>

        <div className="stage-filters">
          <button
            type="button"
            className={stageFilter === null ? "chip-button chip-button--active" : "chip-button"}
            onClick={() => setStageFilter(null)}
          >
            All ({totalProjects})
          </button>
          {WORKFLOW_STAGES.filter((s) => (stageCounts[s.key] || 0) > 0).map((s) => (
            <button
              key={s.key}
              type="button"
              className={stageFilter === s.key ? "chip-button chip-button--active" : "chip-button"}
              onClick={() => setStageFilter(stageFilter === s.key ? null : s.key)}
            >
              {s.label} ({stageCounts[s.key] || 0})
            </button>
          ))}
        </div>

        <div className="flex items-center rounded-lg border border-border-subtle bg-glass p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("grid")}
            className={`inline-flex items-center justify-center h-8 w-8 rounded-md transition-all duration-200 ${viewMode === "grid" ? "bg-primary-bg text-primary shadow-sm" : "text-muted hover:text-primary"}`}
            aria-label="Grid view"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={`inline-flex items-center justify-center h-8 w-8 rounded-md transition-all duration-200 ${viewMode === "list" ? "bg-primary-bg text-primary shadow-sm" : "text-muted hover:text-primary"}`}
            aria-label="List view"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          </button>
        </div>
      </div>

      {/* Project Cards */}
      {filteredProjects.length > 0 ? (
        viewMode === "grid" ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 animate-fade-in-up">
            {filteredProjects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-3 animate-fade-in-up">
            {filteredProjects.map((project) => (
              <ProjectListRow key={project.id} project={project} />
            ))}
          </div>
        )
      ) : (
        search || stageFilter ? (
          <div className="projects-empty">
            <div className="projects-empty__icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </div>
            <h3 className="font-heading text-lg font-bold text-primary">No matching projects</h3>
            <p className="text-secondary max-w-sm text-sm">Try adjusting your search or clearing the filters to see all projects.</p>
            <button type="button" className="btn-ghost" onClick={() => { setSearch(""); setStageFilter(null); }}>
              Clear filters
            </button>
          </div>
        ) : (
          <div className="projects-empty">
            <div className="projects-empty__icon">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>
            </div>
            <h3 className="font-heading text-xl font-bold text-primary">Create your first project</h3>
            <p className="text-secondary max-w-md text-sm leading-relaxed">
              Start by creating a new project. Each project guides you through brief, ideas, script, scenes, and renders to produce a polished video.
            </p>
            <button type="button" className="btn-primary" onClick={() => setQuickCreateOpen(true)}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              New Project
            </button>
          </div>
        )
      )}

      <QuickCreateProjectModal
        open={isQuickCreateOpen}
        onClose={() => setQuickCreateOpen(false)}
      />
    </PageFrame>
  );
}

function ProjectListRow({ project }: { project: ProjectSummary }) {
  const gradient = stageGradients[project.stage] ?? stageGradients.brief;
  const currentStage = WORKFLOW_STAGES.find((s) => s.key === project.stage);

  return (
    <div className="group flex items-center gap-4 rounded-xl border border-border-card bg-card px-5 py-4 transition-all duration-200 hover:border-border-active hover:shadow-md hover:-translate-y-px animate-rise-in">
      <span className="inline-block h-10 w-1 rounded-full shrink-0" style={{ background: gradient }} />

      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[0.65rem] font-bold uppercase tracking-widest text-muted">{project.client}</span>
          <span className="text-[0.5rem] text-muted">·</span>
          <span className="inline-flex items-center gap-1 text-[0.7rem] font-semibold capitalize" style={{ color: "var(--accent)" }}>
            <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: gradient }} />
            {currentStage?.label ?? project.stage}
          </span>
        </div>
        <h3 className="font-heading text-sm font-bold text-primary leading-snug truncate">{project.title}</h3>
        {project.hook && <p className="text-xs text-secondary truncate">{project.hook}</p>}
      </div>

      <div className="hidden md:flex items-center gap-5 shrink-0">
        <ProjectWorkflowDots stage={project.stage} />
      </div>

      <div className="hidden lg:flex items-center gap-4 text-xs text-muted shrink-0">
        <span className="inline-flex items-center gap-1">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><path d="M8 21h8M12 17v4"/></svg>
          {project.sceneCount}
        </span>
        {project.durationSec > 0 && (
          <span className="inline-flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {formatDuration(project.durationSec)}
          </span>
        )}
        <span className="text-[0.7rem]">{relativeTime(project.updatedAt)}</span>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <StatusBadge status={project.renderStatus} />
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Link className="btn-ghost !min-h-[2rem] !px-3 !py-1 !text-xs" to={`/app/projects/${project.id}/${project.stage}`}>
          Continue
        </Link>
        <Link className="btn-primary !min-h-[2rem] !px-3 !py-1 !text-xs" to={`/app/projects/${project.id}/brief`}>
          Open
        </Link>
      </div>
    </div>
  );
}

export function ProjectBriefPage() {
  const { bundle, isLoading, projectId } = useProjectData();
  const navigate = useNavigate();
  const { data: briefData } = useBrief(projectId);
  const { data: quickCreateStatus } = useQuickCreateStatus(projectId);
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
  const quickCreateBanner = activeQuickStart(quickCreateStatus);
  const isQuickCreateLocked = quickCreateStatus?.isActive ?? false;
  const isBriefEmpty = !brief.objective && !brief.hook && !brief.targetAudience && !brief.callToAction;

  return (
    <PageFrame
      eyebrow="Brief workspace"
      title={bundle.project.title}
      description="The brief sets the production atmosphere, hard constraints, and approval path before any expensive generation begins."
      actions={
        quickCreateBanner?.isActive ? null : <div style={{ display: "flex", gap: "0.75rem" }}>
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
      {quickCreateBanner ? <QuickStartStatusBanner status={quickCreateBanner} compact /> : null}
      {isQuickCreateLocked && isBriefEmpty ? (
        <SectionCard className="surface-card--hero" title="Synthesizing the project brief" subtitle="The quick-start flow is still turning your idea into a structured brief.">
          <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
            This screen stays read-only until the bootstrap reaches the next step. You can follow the progress from the banner above.
          </p>
        </SectionCard>
      ) : null}
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
              disabled={isQuickCreateLocked}
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
                disabled={isQuickCreateLocked}
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
                disabled={isQuickCreateLocked}
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
                disabled={isQuickCreateLocked}
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
                disabled={isQuickCreateLocked}
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
  const { data: quickCreateStatus } = useQuickCreateStatus(projectId);
  const [queuedGeneration, setQueuedGeneration] = useState(false);

  const { data: freshScript, isLoading: isScriptLoading } = useScript(projectId);

  useEffect(() => {
    if (freshScript && freshScript.id !== `queued-${projectId}`) {
      setQueuedGeneration(false);
    }
  }, [freshScript, projectId]);

  if (isLoading || isScriptLoading || !bundle) {
    return <LoadingPage />;
  }

  const quickCreateBanner = activeQuickStart(quickCreateStatus);
  const isQuickCreateLocked = quickCreateStatus?.isActive ?? false;

  /* ── Empty state ──────────────────────────────────────────────────────── */
  if (!freshScript && !generateScript.isPending && !queuedGeneration && !isQuickCreateLocked) {
    return (
      <div className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
        <div className="script-empty">
          <div className="script-empty__icon">
            <ScriptDocIcon />
          </div>
          <div className="flex flex-col gap-2 max-w-md">
            <h3 className="font-heading text-xl font-bold text-primary">Ready to write your script</h3>
            <p className="text-[0.9rem] leading-relaxed text-secondary">
              Generate an AI-powered script from your selected idea. Each scene will include narration, visual direction, and voice pacing cues.
            </p>
          </div>
          <div className="flex flex-col gap-2 text-left max-w-sm w-full">
            {[
              { label: "Scene narration", detail: "Polished voiceover text for each beat" },
              { label: "Visual direction", detail: "Shot framing and motion cues per scene" },
              { label: "Voice pacing", detail: "Tempo and delivery annotations throughout" },
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
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setQueuedGeneration(true);
                generateScript.mutate();
              }}
            >
              <ScriptSparklesIcon />
              Generate script
            </button>
            <Link className="btn-ghost" to={`/app/projects/${projectId}/ideas`}>
              Back to ideas
            </Link>
          </div>
        </div>
      </div>
    );
  }

  /* ── Generating state ─────────────────────────────────────────────────── */
  if (
    generateScript.isPending ||
    queuedGeneration ||
    freshScript?.approvalState === "queued" ||
    (!freshScript && isQuickCreateLocked)
  ) {
    return (
      <PageFrame
        eyebrow="Script workspace"
        title="Generating script..."
        description="The AI is drafting narration and visual direction from your selected idea."
        inspector={
          <div className="inspector-stack">
            <div className="flex flex-col gap-3 p-5 rounded-xl bg-card border border-border-card shadow-card animate-rise-in">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center justify-between gap-3 rounded-xl bg-glass px-3 py-2.5">
                  <div className="shimmer h-3 w-16 rounded-full" />
                  <div className="shimmer h-3 w-20 rounded-full" />
                </div>
              ))}
            </div>
          </div>
        }
      >
        {quickCreateBanner ? <QuickStartStatusBanner status={quickCreateBanner} /> : null}
        <SectionCard className="surface-card--hero" title="Writing your script..." subtitle="Crafting narration and visual cues for each scene">
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-[3px] border-border-subtle border-t-accent rounded-full animate-spin shrink-0" />
              <span className="text-sm font-semibold text-secondary">Analyzing idea and generating scene beats...</span>
            </div>
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-4 rounded-xl border border-border-subtle bg-glass p-4">
                  <div className="shimmer h-8 w-8 rounded-lg shrink-0" />
                  <div className="flex-1 flex flex-col gap-2.5">
                    <div className="flex items-center gap-3">
                      <div className="shimmer h-3 w-16 rounded-full" />
                      <div className="shimmer h-4 w-32 rounded-full" />
                    </div>
                    <div className="shimmer h-3 w-full rounded-full" />
                    <div className="shimmer h-3 w-5/6 rounded-full" />
                    <div className="flex gap-3 mt-1 pt-2 border-t border-border-subtle">
                      <div className="shimmer h-3 w-28 rounded-full" />
                      <div className="shimmer h-3 w-20 rounded-full" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      </PageFrame>
    );
  }

  const scriptData = freshScript;
  if (!scriptData) return null;

  const isApproved = scriptData.approvalState === "approved";
  const totalDuration = scriptData.lines.reduce((sum, l) => sum + l.durationSec, 0);

  /* ── Main script view ─────────────────────────────────────────────────── */
  return (
    <PageFrame
      eyebrow="Script workspace"
      title={`${bundle.project.title} · ${scriptData.versionLabel}`}
      description="Review the AI-generated script with narration, visual direction, and pacing cues for every scene."
      actions={
        <div className="flex items-center gap-3">
          <Link className="btn-ghost" to={`/app/projects/${projectId}/ideas`}>
            Back to ideas
          </Link>
          {isQuickCreateLocked ? null : !isApproved ? (
            <>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => {
                  setQueuedGeneration(true);
                  generateScript.mutate();
                }}
                disabled={generateScript.isPending}
              >
                <ScriptSparklesIcon />
                Regenerate
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => approveScript.mutate()}
                disabled={approveScript.isPending}
              >
                <ScriptCheckIcon />
                {approveScript.isPending ? "Approving..." : "Approve script"}
              </button>
            </>
          ) : (
            <>
              <span className="approval-badge approval-badge--approved">Approved</span>
              <Link className="btn-primary" to={`/app/projects/${projectId}/scenes`}>
                Segment into scenes
                <ScriptArrowIcon />
              </Link>
            </>
          )}
        </div>
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
                <strong>{scriptData.totalWords.toLocaleString()}</strong>
              </div>
              <div>
                <span>Reading time</span>
                <strong>{scriptData.readingTimeLabel}</strong>
              </div>
              <div>
                <span>Scene count</span>
                <strong>{scriptData.lines.length}</strong>
              </div>
              <div>
                <span>Total duration</span>
                <strong>{formatDuration(totalDuration)}</strong>
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
      {quickCreateBanner ? <QuickStartStatusBanner status={quickCreateBanner} compact /> : null}

      {/* Stats ribbon */}
      <div className="script-stats">
        {[
          { label: "Word count", value: scriptData.totalWords.toLocaleString(), bg: "bg-primary-bg", fg: "text-primary-fg" },
          { label: "Reading time", value: scriptData.readingTimeLabel, bg: "bg-[rgba(14,165,233,0.12)]", fg: "text-accent-secondary" },
          { label: "Voice preset", value: bundle.project.voicePreset, bg: "bg-[rgba(168,85,247,0.12)]", fg: "text-[#a855f7]" },
          { label: "Approval", value: scriptData.approvalState, bg: isApproved ? "bg-success-bg" : "bg-warning-bg", fg: isApproved ? "text-success" : "text-warning" },
        ].map((stat) => (
          <div key={stat.label} className="stat-card animate-rise-in">
            <div className={`stat-card__icon ${stat.bg} ${stat.fg}`}>
              {stat.label === "Word count" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" /></svg>
              ) : stat.label === "Reading time" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
              ) : stat.label === "Voice preset" ? (
                <ScriptMicIcon size={18} />
              ) : (
                <ScriptCheckIcon size={18} />
              )}
            </div>
            <div className="flex flex-col">
              <span className="stat-card__value">{stat.value}</span>
              <span className="stat-card__label">{stat.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Script lines */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col gap-0.5">
            <h3 className="font-heading text-[1.05rem] font-bold text-primary">Script lines</h3>
            <p className="text-[0.85rem] text-secondary">
              {scriptData.lines.length} scenes with narration, visual direction, and pacing cues
            </p>
          </div>
          <span className="text-[0.7rem] font-bold text-muted px-3 py-1.5 rounded-full bg-glass border border-border-subtle uppercase tracking-wider whitespace-nowrap">
            {formatDuration(totalDuration)} total
          </span>
        </div>
        <div className="flex flex-col gap-3">
          {scriptData.lines.map((line, index) => (
            <ScriptLineCard key={line.id} line={line} index={index} />
          ))}
        </div>
      </div>
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


const PRESET_CATEGORIES = [
  { key: "visual", label: "Visual", gradient: "linear-gradient(135deg, #8b5cf6, #a855f7)" },
  { key: "voice", label: "Voice", gradient: "linear-gradient(135deg, #3b82f6, #2563eb)" },
  { key: "music", label: "Music", gradient: "linear-gradient(135deg, #f59e0b, #f97316)" },
  { key: "subtitle", label: "Subtitle", gradient: "linear-gradient(135deg, #10b981, #059669)" },
] as const;

function presetCategoryMeta(category: string) {
  return PRESET_CATEGORIES.find((c) => c.key === category) ?? PRESET_CATEGORIES[0];
}

function PresetCategoryIcon({ category, size = 18 }: { category: string; size?: number }) {
  switch (category) {
    case "visual":
      return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="13.5" cy="6.5" r="2.5"/><path d="M17.35 6.77a8 8 0 11-9.41 1.6"/><path d="M6.5 12.5A4 4 0 004 16a4 4 0 004 0 4 4 0 004 0 4 4 0 002.5-3.5"/></svg>;
    case "voice":
      return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>;
    case "music":
      return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>;
    case "subtitle":
      return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="7" y1="15" x2="17" y2="15"/><line x1="7" y1="11" x2="13" y2="11"/></svg>;
    default:
      return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>;
  }
}

function PresetCardItem({ preset }: { preset: import("../types/domain").PresetCard }) {
  const meta = presetCategoryMeta(preset.category);
  const detailLines: Array<{ label: string; value: string }> = [];
  if (preset.look) detailLines.push({ label: "Look", value: preset.look });
  if (preset.voice) detailLines.push({ label: "Voice ID", value: preset.voice });
  if (preset.transitionMode) detailLines.push({ label: "Transition", value: preset.transitionMode });

  return (
    <div className="project-card group">
      <div className="project-card__accent" style={{ background: meta.gradient }} />
      <div className="project-card__body">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white" style={{ background: meta.gradient }}>
            <PresetCategoryIcon category={preset.category} size={18} />
          </div>
          <div className="flex flex-col gap-0.5 min-w-0 flex-1">
            <h3 className="project-card__title">{preset.name}</h3>
            <p className="text-xs text-secondary leading-relaxed line-clamp-2">{preset.description}</p>
          </div>
        </div>

        {/* Category + status */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[0.7rem] font-semibold capitalize" style={{ color: "var(--accent)" }}>
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: meta.gradient }} />
            {meta.label}
          </span>
          <span className="text-[0.5rem] text-muted">·</span>
          <span className={`inline-flex items-center gap-1 text-[0.7rem] font-medium ${preset.status === "active" ? "text-success" : "text-muted"}`}>
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${preset.status === "active" ? "bg-success" : "bg-neutral"}`} />
            {preset.status === "active" ? "Active" : preset.status}
          </span>
        </div>

        {/* Detail rows */}
        {detailLines.length > 0 && (
          <div className="flex flex-col gap-2 rounded-lg bg-glass p-3">
            {detailLines.map((d) => (
              <div key={d.label} className="flex items-start justify-between gap-3">
                <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted shrink-0">{d.label}</span>
                <span className="text-xs text-primary text-right font-medium">{d.value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Tags */}
        {preset.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {preset.tags.map((tag) => (
              <span className="inline-flex items-center rounded-md bg-glass px-2 py-0.5 text-[0.68rem] font-medium text-muted" key={tag}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function PresetsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["presets"],
    queryFn: mockGetPresets,
  });
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const filteredPresets = useMemo(() => {
    if (!data) return [];
    let list = [...data];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    if (categoryFilter) {
      list = list.filter((p) => p.category === categoryFilter);
    }
    return list;
  }, [data, search, categoryFilter]);

  const categoryCounts = useMemo(() => {
    if (!data) return {};
    const counts: Record<string, number> = {};
    for (const p of data) {
      counts[p.category] = (counts[p.category] || 0) + 1;
    }
    return counts;
  }, [data]);

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  const activeCount = data.filter((p) => p.status === "active").length;

  return (
    <PageFrame
      eyebrow="Presets"
      title="Your Presets"
      description="Reusable visual, voice, music, and subtitle presets that keep your projects consistent."
      actions={
        <Link className="btn-ghost" to="/app/templates">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><circle cx="17.5" cy="17.5" r="3.5"/></svg>
          Browse Templates
        </Link>
      }
      inspector={
        <div className="inspector-stack">
          {/* Overview */}
          <SectionCard title="Overview">
            <div className="flex flex-col gap-3">
              <div className="stat-card">
                <div className="stat-card__icon bg-primary-bg text-accent">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{data.length}</span>
                  <span className="stat-card__label">Total presets</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-card__icon bg-success-bg text-success">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
                <div className="flex flex-col">
                  <span className="stat-card__value">{activeCount}</span>
                  <span className="stat-card__label">Active</span>
                </div>
              </div>
            </div>
          </SectionCard>

          {/* By category */}
          <SectionCard title="By Category">
            <div className="flex flex-col gap-2">
              {PRESET_CATEGORIES.map((cat) => {
                const count = categoryCounts[cat.key] || 0;
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => setCategoryFilter(categoryFilter === cat.key ? null : cat.key)}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs transition-all duration-200 cursor-pointer ${
                      categoryFilter === cat.key
                        ? "bg-primary-bg border border-border-active text-primary font-semibold"
                        : "bg-transparent hover:bg-glass border border-transparent text-secondary hover:text-primary"
                    }`}
                  >
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white" style={{ background: cat.gradient }}>
                      <PresetCategoryIcon category={cat.key} size={14} />
                    </span>
                    <span className="flex-1 text-left">{cat.label}</span>
                    <span className="font-bold text-primary">{count}</span>
                  </button>
                );
              })}
            </div>
          </SectionCard>
        </div>
      }
    >
      {/* Toolbar */}
      <div className="projects-toolbar">
        <div className="relative flex-1 min-w-0">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input
            className="projects-search !pl-10"
            placeholder="Search presets by name, description, or tag..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search presets"
          />
        </div>
        <div className="stage-filters">
          <button
            type="button"
            className={categoryFilter === null ? "chip-button chip-button--active" : "chip-button"}
            onClick={() => setCategoryFilter(null)}
          >
            All ({data.length})
          </button>
          {PRESET_CATEGORIES.filter((c) => (categoryCounts[c.key] || 0) > 0).map((cat) => (
            <button
              key={cat.key}
              type="button"
              className={categoryFilter === cat.key ? "chip-button chip-button--active" : "chip-button"}
              onClick={() => setCategoryFilter(categoryFilter === cat.key ? null : cat.key)}
            >
              {cat.label} ({categoryCounts[cat.key] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* Preset grid */}
      {filteredPresets.length > 0 ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 animate-fade-in-up">
          {filteredPresets.map((preset) => (
            <PresetCardItem key={preset.id} preset={preset} />
          ))}
        </div>
      ) : search || categoryFilter ? (
        <div className="projects-empty">
          <div className="projects-empty__icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </div>
          <h3 className="font-heading text-lg font-bold text-primary">No matching presets</h3>
          <p className="text-secondary max-w-sm text-sm">Try adjusting your search or clearing the category filter.</p>
          <button type="button" className="btn-ghost" onClick={() => { setSearch(""); setCategoryFilter(null); }}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="projects-empty">
          <div className="projects-empty__icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          </div>
          <h3 className="font-heading text-xl font-bold text-primary">No presets yet</h3>
          <p className="text-secondary max-w-md text-sm leading-relaxed">
            Presets define reusable visual styles, voice settings, music beds, and subtitle configurations for your projects.
          </p>
          <Link className="btn-primary" to="/app/templates">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><circle cx="17.5" cy="17.5" r="3.5"/></svg>
            Browse Templates
          </Link>
        </div>
      )}
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
