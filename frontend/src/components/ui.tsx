import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { mockGetShellData } from "../lib/mock-service";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { formatDuration, formatPercent, titleFromStatus } from "../lib/format";
import { useStudioUiStore } from "../state/ui-store";
import type {
  AlertItem,
  HealthTone,
  ProjectSummary,
  ScenePlan,
  WorkspaceSummary,
} from "../types/domain";

export function LoadingPage() {
  return (
    <div className="flex items-center justify-center h-full min-h-[300px]">
      <div className="w-6 h-6 border-4 border-border-subtle border-t-primary rounded-full animate-spin"></div>
    </div>
  );
}

function AppBackdrop() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 -z-10 bg-base [background-image:radial-gradient(circle_at_top_left,rgba(47,109,246,0.14),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.1),transparent_24%)] dark:[background-image:radial-gradient(circle_at_top_left,rgba(91,140,255,0.22),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.12),transparent_24%),linear-gradient(180deg,rgba(8,17,31,0.85),rgba(8,17,31,1))]"
    />
  );
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      className="inline-flex items-center gap-2 rounded-full border border-border-subtle bg-glass px-3 py-1.5 text-xs font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover"
      onClick={toggleTheme}
      type="button"
    >
      <span>{theme === "dark" ? "Light" : "Dark"} mode</span>
    </button>
  );
}

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
  library:   "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14 M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z M5 3h2 M9 3h2 M13 3h2",
};

const navIconMap: Record<string, string> = {
  "Dashboard":      icons.dashboard,
  "Videos":         icons.scenes,
  "Projects":       icons.projects,
  "Presets":        icons.presets,
  "Templates":      icons.templates,
  "Video Library":  icons.library,
  "Brief":     icons.brief,
  "Ideas":     icons.ideas,
  "Script":    icons.script,
  "Scenes":    icons.scenes,
  "Renders":   icons.renders,
  "Editor":    "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z",
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
  { key: "editor", label: "Editor" },
  { key: "exports", label: "Exports" },
];

const defaultProjectId = "project_aurora_serum";

/* ─── Status helpers ──────────────────────────────────────────────────────── */
function statusClassName(value: string): string {
  const normalized = value.toLowerCase().replace(/\s+/g, "_");

  const baseBadge = "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest border transition-colors";
  if (
    normalized.includes("approved") ||
    normalized.includes("completed") ||
    normalized.includes("ready") ||
    normalized.includes("pass") ||
    normalized.includes("healthy")
  ) {
    return `${baseBadge} bg-success-bg text-success border-success-glow`;
  }

  if (
    normalized.includes("running") ||
    normalized.includes("active") ||
    normalized.includes("live") ||
    normalized.includes("primary")
  ) {
    return `${baseBadge} bg-primary-bg text-primary-fg border-border-active shadow-[0_0_10px_var(--accent-glow-sm)]`;
  }

  if (
    normalized.includes("warning") ||
    normalized.includes("blocked") ||
    normalized.includes("review") ||
    normalized.includes("pending") ||
    normalized.includes("load")
  ) {
    return `${baseBadge} bg-warning-bg text-warning border-warning-bg`;
  }

  if (normalized.includes("fail") || normalized.includes("error") || normalized.includes("offline")) {
    return `${baseBadge} bg-error-bg text-error border-error-bg`;
  }

  return `${baseBadge} bg-neutral-bg text-neutral border-border-subtle`;
}

function toneClassName(tone: HealthTone): string {
  const base = "inline-flex w-[0.55rem] h-[0.55rem] mt-[0.38rem] rounded-full shrink-0";
  switch(tone) {
    case 'neutral': return `${base} bg-neutral`;
    case 'primary': return `${base} bg-accent shadow-[0_0_6px_var(--accent-glow)]`;
    case 'success': return `${base} bg-success`;
    case 'warning': return `${base} bg-warning`;
    case 'error': return `${base} bg-error`;
    default: return `${base} bg-neutral`;
  }
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

/* ─── Notification Dropdown ────────────────────────────────────────────────── */
function NotificationDropdown({ alerts }: { alerts: AlertItem[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const dismiss = useCallback((id: string) => {
    void id;
  }, []);

  const unreadCount = alerts.length;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="relative flex items-center gap-2 rounded-full border border-border-card bg-glass px-3 py-1 text-xs text-secondary hover:border-border-active transition-colors cursor-pointer"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={`Notifications – ${unreadCount} alerts`}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-error text-[0.6rem] font-bold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-border-card bg-surface shadow-lg z-50 overflow-hidden animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted">Notifications</h3>
            <span className="text-[0.7rem] text-secondary">{unreadCount} alert{unreadCount !== 1 ? "s" : ""}</span>
          </div>
          {alerts.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-muted">No notifications</div>
          ) : (
            <div className="max-h-72 overflow-y-auto">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start gap-3 px-4 py-3 border-b border-border-subtle last:border-b-0 hover:bg-glass/60 transition-colors"
                >
                  <span className={toneClassName(alert.tone)} />
                  <div className="flex-1 min-w-0">
                    <strong className="block text-[0.8rem] font-semibold text-primary leading-tight">{alert.label}</strong>
                    <p className="text-[0.75rem] text-secondary leading-snug mt-0.5">{alert.detail}</p>
                  </div>
                  <button
                    type="button"
                    className="shrink-0 text-muted hover:text-primary transition-colors text-xs mt-0.5"
                    aria-label={`Dismiss ${alert.label}`}
                    onClick={() => dismiss(alert.id)}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Shell Layout ────────────────────────────────────────────────────────── */
export function ShellLayout({ mode }: { mode: "app" | "admin" }) {
  const location = useLocation();
  const { logout, workspaceId, selectWorkspace, isLoading: isAuthLoading } = useAuth();
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

  useEffect(() => {
    if (!data) {
      return;
    }
    const preferredWorkspaceId = workspaceId ?? data.workspaces[0]?.id ?? "";
    if (preferredWorkspaceId && preferredWorkspaceId !== activeWorkspaceId) {
      setActiveWorkspaceId(preferredWorkspaceId);
    }
    if (!routeProjectId && !activeProjectId && data.projects[0]?.id) {
      setActiveProjectId(data.projects[0].id);
    }
  }, [activeProjectId, activeWorkspaceId, data, routeProjectId, setActiveProjectId, setActiveWorkspaceId, workspaceId]);

  if (isLoading || isAuthLoading || !data) {
    return (
      <div className="relative flex h-screen w-full overflow-hidden bg-base text-primary antialiased">
        <AppBackdrop />
        <aside className="w-64 flex-shrink-0 border-r border-border-subtle bg-surface/80 shimmer" />
        <main className="flex-1 flex flex-col min-w-0">
          <div className="h-14 w-full bg-surface/80 border-b border-border-subtle shimmer" />
          <div className="p-8">
            <div className="h-64 rounded-xl border border-border-card bg-card shimmer" />
          </div>
        </main>
      </div>
    );
  }

  const activeWorkspace = findActiveWorkspace(data.workspaces, activeWorkspaceId || workspaceId || data.workspaces[0]?.id || "");
  const currentProject = findActiveProject(
    data.projects,
    routeProjectId ?? activeProjectId ?? data.projects[0]?.id ?? defaultProjectId,
  );
  const currentWorkflowStep = getCurrentWorkflowStep(location.pathname);

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-base text-primary antialiased">
      <AppBackdrop />
      <aside className="no-scrollbar w-64 flex-shrink-0 flex flex-col gap-6 overflow-y-auto border-r border-border-subtle bg-surface/80 p-4 backdrop-blur-md">
        {/* Brand */}
        <div className="flex items-center gap-3 px-2">
          <div className="h-6 w-6 rounded bg-accent-gradient flex-shrink-0 shadow-accent z-10" aria-hidden="true" />
          <div>
            <p className="text-[0.6rem] font-bold uppercase tracking-widest text-muted mb-0.5">Production Atelier</p>
            <h1 className="text-xs font-heading font-bold tracking-wide text-primary">Reels Generation Studio</h1>
          </div>
        </div>

        {/* Workspace switcher */}
        <div className="flex flex-col gap-2 rounded-lg border border-border-subtle bg-glass p-3">
          <label className="text-[0.65rem] font-bold uppercase tracking-wider text-muted mb-0.5" htmlFor="workspace-select">
            Workspace
          </label>
          <select
            id="workspace-select"
            className="w-full bg-card border border-border-card rounded flex-1 py-1.5 px-2 text-xs text-primary shadow-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
            value={activeWorkspace.id}
            onChange={(event) => {
              const nextWorkspaceId = event.target.value;
              setActiveWorkspaceId(nextWorkspaceId);
              void selectWorkspace(nextWorkspaceId);
            }}
          >
            {data.workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))}
          </select>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-border-subtle text-[0.65rem] uppercase tracking-wider text-muted">
            <div className="flex flex-col">
              <span>Credits</span>
              <strong className="text-primary text-[0.82rem] font-semibold normal-case mt-0.5">
                {activeWorkspace.creditsRemaining} / {activeWorkspace.creditsTotal}
              </strong>
            </div>
            <div className="flex flex-col text-right">
              <span>Queue</span>
              <strong className="text-primary text-[0.82rem] font-semibold normal-case mt-0.5">{activeWorkspace.queueCount} active</strong>
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
                { to: "/app/videos", label: "Videos" },
                { to: "/app/projects", label: "Projects" },
                { to: "/app/assets", label: "Assets" },
                { to: "/app/video-library", label: "Video Library" },
                { to: "/app/presets", label: "Presets" },
                { to: "/app/templates", label: "Templates" },
              ]}
            />

            <div className="flex flex-col gap-2 rounded-lg border border-border-subtle bg-glass p-3">
              <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Active Project</p>
              <div className="flex flex-col gap-1.5 rounded-xl border border-border-card bg-card p-3 shadow-sm mt-1">
                <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">{currentProject.client}</p>
                <h2 className="font-heading font-bold text-sm text-primary leading-snug">{currentProject.title}</h2>
                <div className="mt-1"><StatusBadge status={currentProject.renderStatus} /></div>
                <p className="text-xs text-secondary mt-1 max-w-[90%] whitespace-nowrap overflow-hidden text-ellipsis">{currentProject.nextMilestone}</p>
              </div>
              <div className="mt-2">
                <NavGroup
                  label="Workflow"
                  compact
                  items={[
                    { to: `/app/projects/${currentProject.id}/brief`, label: "Brief" },
                    { to: `/app/projects/${currentProject.id}/ideas`, label: "Ideas" },
                    { to: `/app/projects/${currentProject.id}/script`, label: "Script" },
                    { to: `/app/projects/${currentProject.id}/scenes`, label: "Scenes" },
                    { to: `/app/projects/${currentProject.id}/frames`, label: "Frames" },
                    { to: `/app/projects/${currentProject.id}/renders`, label: "Renders" },
                    { to: `/app/projects/${currentProject.id}/editor`, label: "Editor" },
                    { to: `/app/projects/${currentProject.id}/exports`, label: "Exports" },
                  ]}
                />
              </div>
            </div>

            <NavGroup
              label="Operations"
              items={[
                { to: "/app/settings/brand", label: "Brand Kits" },
                { to: "/app/settings/team", label: "Team Settings" },
                { to: "/app/settings/providers", label: "API Keys" },
                { to: "/app/settings/workers", label: "Local Workers" },
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

            <div className="flex flex-col gap-2 rounded-lg border border-border-subtle bg-glass p-3">
              <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Return To Studio</p>
              <Link
                className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px w-full mt-2"
                to="/app"
              >
                Open creator workspace
              </Link>
            </div>
          </>
        )}

      </aside>

      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto relative no-scrollbar">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b border-border-subtle bg-surface/80 px-6 backdrop-blur-md sticky top-0 z-20">
          <div className="flex flex-col">
            <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">{mode === "app" ? activeWorkspace.plan : "Admin operations"}</p>
            <h2 className="font-heading text-sm font-bold text-primary leading-tight">{mode === "app" ? activeWorkspace.name : "Render operations desk"}</h2>
          </div>
          <div className="flex items-center gap-4">
            <input
              className="min-w-[16rem] px-4 py-1.5 rounded-full border border-border-subtle bg-glass text-xs text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)] placeholder:text-muted"
              placeholder="Search projects, renders, presets…"
              readOnly
              aria-label="Search"
            />
            <ThemeToggle />
            <div className="flex items-center gap-2 rounded-full border border-border-card bg-glass px-3 py-1 text-xs text-secondary hover:border-border-active transition-colors cursor-default">
              <span>Queue</span>
              <strong className="text-primary font-semibold">{activeWorkspace.queueCount} active</strong>
            </div>
            <NotificationDropdown alerts={data.alerts} />
            <div className="flex items-center gap-2 pl-3 border-l border-border-subtle py-1">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent-gradient text-xs font-bold text-on-accent shadow-accent" aria-hidden="true">{data.user.avatarInitials}</span>
              <div className="flex flex-col">
                <strong className="text-[0.85rem] font-semibold text-primary">{data.user.name}</strong>
                <p className="text-[0.7rem] text-muted">{data.user.role}</p>
              </div>
            </div>
            <button
              className="inline-flex items-center justify-center gap-2 px-3 py-1 rounded-md font-medium text-[0.75rem] transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active"
              onClick={() => logout()}
              type="button"
            >
              Sign out
            </button>
          </div>
        </header>

        {mode === "app" && routeProjectId ? (
          <div className="pt-6 px-7">
            <ProjectContextBar
              currentStep={currentWorkflowStep}
              project={currentProject}
            />
          </div>
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
    <div className="flex flex-col gap-1">
      <p className="text-[0.65rem] font-bold uppercase tracking-wider text-muted px-2 mb-1">{label}</p>
      <div className={compact ? "flex flex-col gap-0.5" : "flex flex-col gap-1"}>
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) =>
              isActive 
                ? "flex items-center gap-3 rounded-md px-3 py-2 text-[0.875rem] font-semibold text-accent-bright bg-primary-bg transition-all duration-200 shadow-[inset_2.5px_0_0_0_var(--accent)]" 
                : "flex items-center gap-3 rounded-md px-3 py-2 text-[0.875rem] font-medium text-secondary hover:text-primary hover:bg-glass-hover hover:translate-x-0.5 transition-all duration-200"
            }
            to={item.to}
            end={item.to === "/app"}
          >
            <span className="flex items-center gap-2.5">
              {navIconMap[item.label] && (
                <span className="opacity-80"><Icon path={navIconMap[item.label]} size={15} /></span>
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
    <section className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-4 p-4 lg:px-5 rounded-2xl bg-glass border border-border-subtle shadow-sm animate-fade-in-up">
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Current project</p>
          <div className="flex items-center gap-3 flex-wrap mt-1">
            <h3 className="font-heading font-bold text-[1.05rem] text-primary">{project.title}</h3>
            <StatusBadge status={project.renderStatus} />
          </div>
          <p className="text-[0.86rem] text-secondary mt-1">{project.nextMilestone}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-secondary mt-1">
          <span className="inline-flex items-center min-h-[1.8rem] px-3 py-1 rounded-full bg-glass text-[0.78rem]">{titleFromStatus(project.stage)}</span>
          <span className="inline-flex items-center min-h-[1.8rem] px-3 py-1 rounded-full bg-glass text-[0.78rem]">{project.sceneCount} scenes</span>
          <span className="inline-flex items-center min-h-[1.8rem] px-3 py-1 rounded-full bg-glass text-[0.78rem]">{formatDuration(project.durationSec)}</span>
          <span className="inline-flex items-center min-h-[1.8rem] px-3 py-1 rounded-full bg-glass text-[0.78rem]">{project.voicePreset}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center" aria-label="Project workflow">
        {workflowRoutes.map((step) => {
          const isActive = currentStep === step.key;
          return (
            <Link
              className={isActive 
                ? "inline-flex items-center justify-center min-h-[2rem] px-3 py-1.5 rounded-full bg-accent-gradient text-on-accent border border-transparent text-[0.82rem] font-semibold transition-all duration-200 shadow-md" 
                : "inline-flex items-center justify-center min-h-[2rem] px-3 py-1.5 rounded-full bg-glass border border-border-subtle text-secondary text-[0.82rem] font-semibold transition-all duration-200 hover:border-border-active hover:text-primary"}
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
    <section className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up">
      <div className="flex items-end justify-between gap-6 mb-2">
        <div className="flex flex-col gap-1.5">
          <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">{eyebrow}</p>
          <h1 className="font-heading text-3xl md:text-[2.5rem] leading-[1.1] font-bold text-primary tracking-tight">{title}</h1>
          <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch] mt-1">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_19rem] gap-6 items-start">
        <div className="flex flex-col gap-6 min-w-0">{children}</div>
        <aside className="sticky top-20 flex flex-col gap-4 self-start w-full">{inspector}</aside>
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
    <section className={className ? `flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-card transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in ${className}` : "flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-card transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in"}>
      <div className="flex flex-col pb-4 border-b border-border-subtle">
        <h3 className="font-heading text-[1.05rem] font-bold text-primary leading-snug">{title}</h3>
        {subtitle ? <p className="text-[0.86rem] text-secondary mt-1">{subtitle}</p> : null}
      </div>
      <div className="flex flex-col gap-5">
        {children}
      </div>
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
    <div className={`flex flex-col gap-1 p-4 rounded-xl bg-card border border-border-card shadow-sm animate-rise-in tone-${tone}`}>
      <span className="text-[0.6875rem] tracking-widest uppercase font-bold text-muted">{label}</span>
      <strong className="text-2xl font-heading font-bold text-primary mt-1">{value}</strong>
      <p className="text-[0.8rem] text-secondary mt-1">{detail}</p>
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
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-end">
        <span className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted">{label}</span>
        <strong className="text-[0.8rem] font-bold text-accent">{formatPercent(value)}</strong>
      </div>
      <div className="h-1.5 w-full bg-border-subtle rounded-full overflow-hidden shadow-inner">
        <div className="h-full bg-accent-gradient rounded-full transition-all duration-500 ease-out shadow-accent" style={{ width: `${value}%` }} />
      </div>
      {detail ? <p className="text-[0.75rem] text-secondary mt-1">{detail}</p> : null}
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
      className={`relative rounded-xl overflow-hidden flex items-end p-4 border border-border-subtle group ${aspect === "wide" ? "aspect-video" : "aspect-[9/16]"}`}
      style={{ background: gradient }}
    >
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-80" />
      <div className="relative z-10 flex flex-col gap-1 drop-shadow-md">
        <p className="text-[0.65rem] font-bold uppercase tracking-widest text-white/70">{meta}</p>
        <strong className="text-sm font-semibold text-white">{label}</strong>
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
      className={active 
        ? "flex flex-col items-start gap-1.5 p-3.5 rounded-lg bg-primary-bg border border-border-active transition-all duration-200 cursor-pointer text-left shadow-sm animate-rise-in transform scale-[1.01]" 
        : "flex flex-col items-start gap-1.5 p-3.5 rounded-lg bg-card border border-border-subtle transition-all duration-200 cursor-pointer text-left hover:border-border-active animate-rise-in"}
      onClick={onClick}
      type="button"
      aria-pressed={active}
    >
      <div className="flex items-center gap-3 w-full justify-between">
        <span className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">Scene {scene.index}</span>
        <StatusBadge status={scene.status} />
      </div>
      <strong className="text-[0.9rem] font-semibold text-primary mt-1">{scene.title}</strong>
      <p className="text-[0.8rem] text-secondary line-clamp-2 mt-0.5 max-w-[95%]">{scene.beat}</p>
      <div className="flex flex-wrap items-center gap-3 text-[0.7rem] text-muted mt-2">
        <span className="inline-flex items-center justify-center bg-glass px-2 py-0.5 rounded-sm">{scene.durationSec}s</span>
        <span className="inline-flex items-center justify-center bg-glass px-2 py-0.5 rounded-sm">{scene.transitionMode === "crossfade" ? "Crossfade" : "Hard cut"}</span>
        <span className="inline-flex items-center justify-center bg-glass px-2 py-0.5 rounded-sm">{scene.continuityScore}/100 continuity</span>
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
    <div className="flex flex-col items-center justify-center text-center gap-4 py-16 px-6 rounded-2xl bg-card border border-border-card border-dashed">
      <div className="w-12 h-12 rounded-full bg-glass flex items-center justify-center mb-2">
        <Icon path="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" size={24} />
      </div>
      <h3 className="font-heading text-lg font-bold text-primary">{title}</h3>
      <p className="text-secondary max-w-sm">{description}</p>
    </div>
  );
}
