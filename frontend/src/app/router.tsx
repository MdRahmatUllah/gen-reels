import { Navigate, createBrowserRouter } from "react-router-dom";

import { ShellLayout } from "../components/ui";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { LoginPage } from "../routes/login-page";
import { IdeasPage } from "../features/ideas/IdeasPage";
import { ScenesPage } from "../features/scenes/ScenesPage";
import { FramesPage } from "../features/frames/FramesPage";
import { RendersPage } from "../features/renders/RendersPage";
import { ExportsPage } from "../features/exports/ExportsPage";
import { BillingPage } from "../features/billing/BillingPage";
import {
  DashboardPage,
  PresetsPage,
  ProjectBriefPage,
  ProjectsPage,
  ScriptPage,
} from "../routes/app-pages";
import { TemplatesPage } from "../features/templates/TemplatesPage";
import { AssetsPage } from "../features/assets/AssetsPage";
import { BrandKitPage } from "../features/settings/BrandKitPage";
import { TeamSettingsPage } from "../features/settings/TeamSettingsPage";
import { ProviderSettingsPage } from "../features/settings/ProviderSettingsPage";
import { LocalWorkersPage } from "../features/settings/LocalWorkersPage";
import { AdminQueuePage } from "../features/admin/AdminQueuePage";
import { AdminRendersPage } from "../features/admin/AdminRendersPage";
import { AdminWorkspacesPage } from "../features/admin/AdminWorkspacesPage";
import { QuickStartProgressPage } from "../features/projects/QuickStartProgressPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate replace to="/app" />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/app",
    element: (
      <ProtectedRoute>
        <ShellLayout mode="app" />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "projects",
        element: <ProjectsPage />,
      },
      {
        path: "projects/:projectId",
        element: <Navigate replace to="brief" />,
      },
      {
        path: "projects/:projectId/brief",
        element: <ProjectBriefPage />,
      },
      {
        path: "projects/:projectId/quick-start",
        element: <QuickStartProgressPage />,
      },
      {
        path: "projects/:projectId/ideas",
        element: <IdeasPage />,
      },
      {
        path: "projects/:projectId/script",
        element: <ScriptPage />,
      },
      {
        path: "projects/:projectId/scenes",
        element: <ScenesPage />,
      },
      {
        path: "projects/:projectId/frames",
        element: <FramesPage />,
      },
      {
        path: "projects/:projectId/renders",
        element: <RendersPage />,
      },
      {
        path: "projects/:projectId/exports",
        element: <ExportsPage />,
      },
      {
        path: "presets",
        element: <PresetsPage />,
      },
      {
        path: "templates",
        element: <TemplatesPage />,
      },
      {
        path: "assets",
        element: <AssetsPage />,
      },
      {
        path: "settings/brand",
        element: <BrandKitPage />,
      },
      {
        path: "settings/team",
        element: <TeamSettingsPage />,
      },
      {
        path: "settings/providers",
        element: <ProviderSettingsPage />,
      },
      {
        path: "settings/workers",
        element: <LocalWorkersPage />,
      },
      {
        path: "billing",
        element: <BillingPage />,
      },
    ],
  },
  {
    path: "/admin",
    element: (
      <ProtectedRoute>
        <ShellLayout mode="admin" />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate replace to="/admin/queue" />,
      },
      {
        path: "queue",
        element: <AdminQueuePage />,
      },
      {
        path: "workspaces",
        element: <AdminWorkspacesPage />,
      },
      {
        path: "renders",
        element: <AdminRendersPage />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate replace to="/app" />,
  },
]);
