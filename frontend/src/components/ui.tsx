import { type ReactNode, useEffect, useMemo } from "react";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { mockGetShellData } from "../lib/mock-service";
import { useAuth } from "../lib/auth";
import { formatDuration, formatPercent, titleFromStatus } from "../lib/format";
import { useStudioUiStore } from "../state/ui-store";
import type {
  HealthTone,
  ProjectSummary,
  ScenePlan,
  WorkspaceSummary,
} from "../types/domain";

/* ─── Icon Components ─────────────────────────────────────────────────────── */
function Icon({ path, size = 16 }: { path: string; size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <path d={path} />
    </svg>
  );
}

const icons = {
  dashboard: "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10",
  ideas:     "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
  projects:  "M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z",
  presets:   "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
  templates: "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M17 17m-3 0a3 3 0 106 0 3 3 0 00-6 0",
  brief:     "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
  script:    "M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7 M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z",
  scenes:    "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14 M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z",
  renders:   "M5 3l14 9-14 9V3z",
  exports:   "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4 M7 10l5 5 5-5 M12 15V3",
  settings:  "M12 15a3 3 0 100-6 3 3 0 000 6z M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z",
  billing:   "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z M12 6v6l4 2",
  admin:     "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  queue:     "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
  workspaces:"M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  arrow:     "M9 18l6-6-6-6",
};

const navIconMap: Record<string, string> = {
  "Dashboard": icons.dashboard,
  "Projects":  icons.projects,
  "Presets":   icons.presets,
  "Templates": icons.templates,
  "Brief":     icons.brief,
  "Ideas":     icons.ideas,
  "Script":    icons.script,
  "Scenes":    icons.scenes,
  "Renders":   icons.renders,
  "Exports":   icons.exports,
  "Settings":  icons.settings,
  "Billing":   icons.billing,
  "Admin Queue": icons.admin,
  "Queue":     icons.queue,
  "Workspaces": icons.workspaces,
  "Renders (Admin)": icons.renders,
};

const workflowRoutes = [
  { key: "brief", label: "Brief" },
  { key: "ideas", label: "Ideas" },
  { key: "script", label: "Script" },
  { key: "scenes", label: "Scenes" },
  { key: "renders", label: "Renders" },
  { key: "exports", label: "Exports" },
];

const defaultProjectId = "project_aurora_serum";

/* ─── Status helpers ──────────────────────────────────────────────────────── */
function statusClassName(value: string): string {
  const normalized = value.toLowerCase().replace(/\s+/g, "_");

  if (
    normalized.includes("approved") ||
    normalized.includes("completed") ||
    normalized.includes("ready") ||
    normalized.includes("pass") ||
    normalized.includes("healthy")
  ) {
    return "status-badge status-badge--success";
  }

  if (
    normalized.includes("running") ||
    normalized.includes("active") ||
    normalized.includes("live") ||
    normalized.includes("primary")
  ) {
    return "status-badge status-badge--primary";
  }

  if (
    normalized.includes("warning") ||
    normalized.includes("blocked") ||
    normalized.includes("review") ||
    normalized.includes("pending") ||
    normalized.includes("load")
  ) {
    return "status-badge status-badge--warning";
  }

  if (normalized.includes("fail") || normalized.includes("error")) {
    return "status-badge status-badge--error";
  }

  return "status-badge status-badge--neutral";
}

function toneClassName(tone: HealthTone): string {
  return `tone-pill tone-pill--${tone}`;
}

function findActiveProject(projects: ProjectSummary[], projectId: string): ProjectSummary {
  return projects.find((project) => project.id === projectId) ?? projects[0];
}

function findActiveWorkspace(workspaces: WorkspaceSummary[], workspaceId: string): WorkspaceSummary {
  return workspaces.find((workspace) => workspace.id === workspaceId) ?? workspaces[0];
}

function getCurrentWorkflowStep(pathname: string): string | undefined {
  const match = pathname.match(/^\/app\/projects\/[^/]+\/([^/]+)/);
  return match?.[1];
}

/* ─── Shell Layout ────────────────────────────────────────────────────────── */
export function ShellLayout({ mode }: { mode: "app" | "admin" }) {
  const location = useLocation();
  const { logout } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ["shell-data"],
    queryFn: mockGetShellData,
  });
  const activeWorkspaceId = useStudioUiStore((state) => state.activeWorkspaceId);
  const activeProjectId = useStudioUiStore((state) => state.activeProjectId);
  const setActiveProjectId = useStudioUiStore((state) => state.setActiveProjectId);
  const setActiveWorkspaceId = useStudioUiStore((state) => state.setActiveWorkspaceId);

  const routeProjectId = useMemo(() => {
    const match = location.pathname.match(/^\/app\/projects\/([^/]+)/);
    return match?.[1];
  }, [location.pathname]);

  useEffect(() => {
    if (routeProjectId && routeProjectId !== activeProjectId) {
      setActiveProjectId(routeProjectId);
    }
  }, [activeProjectId, routeProjectId, setActiveProjectId]);

  if (isLoading || !data) {
    return (
      <div className="workspace-shell">
        <aside className="nav-rail nav-rail--loading" />
        <main className="workspace-stage">
          <div className="topbar shimmer" style={{ height: "3.5rem" }} />
          <div className="page-shell">
            <div className="surface-card surface-card--loading shimmer" />
          </div>
        </main>
      </div>
    );
  }

  const activeWorkspace = findActiveWorkspace(data.workspaces, activeWorkspaceId);
  const currentProject = findActiveProject(
    data.projects,
    routeProjectId ?? activeProjectId ?? defaultProjectId,
  );
  const currentWorkflowStep = getCurrentWorkflowStep(location.pathname);

  return (
    <div className="workspace-shell">
      <aside className="nav-rail">
        {/* Brand */}
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true" />
          <div>
            <p className="eyebrow">Production Atelier</p>
            <h1>Reels Generation Studio</h1>
          </div>
        </div>

        {/* Workspace switcher */}
        <div className="workspace-switcher">
          <label className="field-label" htmlFor="workspace-select">
            Workspace
          </label>
          <select
            id="workspace-select"
            className="field-input"
            value={activeWorkspace.id}
            onChange={(event) => setActiveWorkspaceId(event.target.value)}
          >
            {data.workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))}
          </select>
          <div className="rail-metric-row">
            <div>
              <span>Credits</span>
              <strong>
                {activeWorkspace.creditsRemaining} / {activeWorkspace.creditsTotal}
              </strong>
            </div>
            <div>
              <span>Queue</span>
              <strong>{activeWorkspace.queueCount} active</strong>
            </div>
          </div>
        </div>

        {/* Navigation */}
        {mode === "app" ? (
          <>
            <NavGroup
              label="Studio"
              items={[
                { to: "/app", label: "Dashboard" },
                { to: "/app/projects", label: "Projects" },
                { to: "/app/presets", label: "Presets" },
                { to: "/app/templates", label: "Templates" },
              ]}
            />

            <div className="surface-panel--rail">
              <p className="section-heading">Active Project</p>
              <div className="rail-project-card" style={{ marginTop: "0.5rem" }}>
                <p className="eyebrow">{currentProject.client}</p>
                <h2>{currentProject.title}</h2>
                <StatusBadge status={currentProject.renderStatus} />
                <p>{currentProject.nextMilestone}</p>
              </div>
              <NavGroup
                label="Workflow"
                compact
                items={[
                  { to: `/app/projects/${currentProject.id}/brief`, label: "Brief" },
                  { to: `/app/projects/${currentProject.id}/ideas`, label: "Ideas" },
                  { to: `/app/projects/${currentProject.id}/script`, label: "Script" },
                  { to: `/app/projects/${currentProject.id}/scenes`, label: "Scenes" },
                  { to: `/app/projects/${currentProject.id}/renders`, label: "Renders" },
                  { to: `/app/projects/${currentProject.id}/exports`, label: "Exports" },
                ]}
              />
            </div>

            <NavGroup
              label="Operations"
              items={[
                { to: "/app/settings", label: "Settings" },
                { to: "/app/billing", label: "Billing" },
                { to: "/admin/queue", label: "Admin Queue" },
              ]}
            />
          </>
        ) : (
          <>
            <NavGroup
              label="Admin"
              items={[
                { to: "/admin/queue", label: "Queue" },
                { to: "/admin/workspaces", label: "Workspaces" },
                { to: "/admin/renders", label: "Renders" },
              ]}
            />

            <div className="surface-panel--rail">
              <p className="section-heading">Return To Studio</p>
              <Link
                className="button button--secondary"
                to="/app"
                style={{ marginTop: "0.5rem", width: "100%", justifyContent: "center" }}
              >
                Open creator workspace
              </Link>
            </div>
          </>
        )}

        {/* Recent signals */}
        <div className="surface-panel--rail">
          <p className="section-heading">Recent signals</p>
          <div className="alert-stack" style={{ marginTop: "0.5rem" }}>
            {data.alerts.map((alert) => (
              <div className="alert-item" key={alert.id}>
                <span className={toneClassName(alert.tone)} />
                <div>
                  <strong>{alert.label}</strong>
                  <p>{alert.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>

      <main className="workspace-stage">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-title">
            <p className="eyebrow">{mode === "app" ? activeWorkspace.plan : "Admin operations"}</p>
            <h2>{mode === "app" ? activeWorkspace.name : "Render operations desk"}</h2>
          </div>
          <div className="topbar-actions">
            <input
              className="search-input"
              placeholder="Search projects, renders, presets…"
              readOnly
              aria-label="Search"
            />
            <div className="topbar-chip">
              <span>Queue</span>
              <strong>{activeWorkspace.queueCount} active</strong>
            </div>
            <div className="topbar-chip">
              <span>Alerts</span>
              <strong>{activeWorkspace.notifications}</strong>
            </div>
            <div className="avatar-chip">
              <span aria-hidden="true">{data.user.avatarInitials}</span>
              <div>
                <strong>{data.user.name}</strong>
                <p>{data.user.role}</p>
              </div>
            </div>
            <button
              className="button button--secondary"
              onClick={() => logout()}
              type="button"
              style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
            >
              Sign out
            </button>
          </div>
        </header>

        {mode === "app" && routeProjectId ? (
          <ProjectContextBar
            currentStep={currentWorkflowStep}
            project={currentProject}
          />
        ) : null}

        <Outlet />
      </main>
    </div>
  );
}

/* ─── NavGroup ────────────────────────────────────────────────────────────── */
function NavGroup({
  label,
  items,
  compact = false,
}: {
  label: string;
  items: Array<{ to: string; label: string }>;
  compact?: boolean;
}) {
  return (
    <div className="nav-group">
      <p className="section-heading">{label}</p>
      <div className={compact ? "nav-group-list nav-group-list--compact" : "nav-group-list"}>
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) =>
              isActive ? "nav-link nav-link--active" : "nav-link"
            }
            to={item.to}
            end={item.to === "/app"}
          >
            <span className="nav-link__label">
              {navIconMap[item.label] && (
                <Icon path={navIconMap[item.label]} size={15} />
              )}
              {item.label}
            </span>
          </NavLink>
        ))}
      </div>
    </div>
  );
}

function ProjectContextBar({
  project,
  currentStep,
}: {
  project: ProjectSummary;
  currentStep?: string;
}) {
  return (
    <section className="context-bar">
      <div className="context-bar__summary">
        <div>
          <p className="eyebrow">Current project</p>
          <div className="context-bar__heading">
            <h3>{project.title}</h3>
            <StatusBadge status={project.renderStatus} />
          </div>
          <p>{project.nextMilestone}</p>
        </div>
        <div className="context-bar__meta">
          <span>{titleFromStatus(project.stage)}</span>
          <span>{project.sceneCount} scenes</span>
          <span>{formatDuration(project.durationSec)}</span>
          <span>{project.voicePreset}</span>
        </div>
      </div>

      <div className="context-bar__steps" aria-label="Project workflow">
        {workflowRoutes.map((step) => {
          const isActive = currentStep === step.key;
          return (
            <Link
              className={isActive ? "context-step context-step--active" : "context-step"}
              key={step.key}
              to={`/app/projects/${project.id}/${step.key}`}
            >
              <span>{step.label}</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

/* ─── PageFrame ───────────────────────────────────────────────────────────── */
export function PageFrame({
  eyebrow,
  title,
  description,
  actions,
  inspector,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  inspector: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="page-shell">
      <div className="page-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="page-title">{title}</h1>
          <p className="page-description">{description}</p>
        </div>
        {actions ? <div className="page-actions">{actions}</div> : null}
      </div>

      <div className="page-grid">
        <div className="page-content">{children}</div>
        <aside className="inspector-panel">{inspector}</aside>
      </div>
    </section>
  );
}

/* ─── SectionCard ─────────────────────────────────────────────────────────── */
export function SectionCard({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className ? `surface-card ${className}` : "surface-card"}>
      <div className="section-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

/* ─── MetricCard ──────────────────────────────────────────────────────────── */
export function MetricCard({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: HealthTone;
}) {
  return (
    <div className={`metric-card metric-card--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

/* ─── StatusBadge ─────────────────────────────────────────────────────────── */
export function StatusBadge({ status }: { status: string }) {
  return <span className={statusClassName(status)}>{titleFromStatus(status)}</span>;
}

/* ─── ProgressBar ─────────────────────────────────────────────────────────── */
export function ProgressBar({
  value,
  label,
  detail,
}: {
  value: number;
  label: string;
  detail?: string;
}) {
  return (
    <div className="progress-block">
      <div className="progress-meta">
        <span>{label}</span>
        <strong>{formatPercent(value)}</strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${value}%` }} />
      </div>
      {detail ? <p className="progress-detail">{detail}</p> : null}
    </div>
  );
}

/* ─── MediaFrame ──────────────────────────────────────────────────────────── */
export function MediaFrame({
  label,
  meta,
  gradient,
  aspect = "vertical",
}: {
  label: string;
  meta: string;
  gradient: string;
  aspect?: "vertical" | "wide";
}) {
  return (
    <div
      className={aspect === "wide" ? "media-frame media-frame--wide" : "media-frame"}
      style={{ background: gradient }}
    >
      <div className="media-frame__overlay">
        <p>{meta}</p>
        <strong>{label}</strong>
      </div>
    </div>
  );
}

/* ─── TimelineItem ────────────────────────────────────────────────────────── */
export function TimelineItem({
  scene,
  active,
  onClick,
}: {
  scene: ScenePlan;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={active ? "timeline-item timeline-item--active" : "timeline-item"}
      onClick={onClick}
      type="button"
      aria-pressed={active}
    >
      <div className="timeline-item__heading">
        <span className="timeline-index">Scene {scene.index}</span>
        <StatusBadge status={scene.status} />
      </div>
      <strong>{scene.title}</strong>
      <p>{scene.beat}</p>
      <div className="timeline-item__meta">
        <span>{scene.durationSec}s</span>
        <span>{scene.transitionMode === "crossfade" ? "Crossfade" : "Hard cut"}</span>
        <span>{scene.continuityScore}/100 consistency</span>
      </div>
    </button>
  );
}

/* ─── EmptyState ──────────────────────────────────────────────────────────── */
export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty-state surface-card">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
