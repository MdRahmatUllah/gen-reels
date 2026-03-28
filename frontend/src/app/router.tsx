import { Navigate, createBrowserRouter } from "react-router-dom";

import { ShellLayout } from "../components/ui";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { LoginPage } from "../routes/login-page";
import { IdeasPage } from "../features/ideas/IdeasPage";
import {
  BillingPage,
  DashboardPage,
  ExportsPage,
  PresetsPage,
  ProjectBriefPage,
  ProjectsPage,
  RendersPage,
  ScenesPage,
  ScriptPage,
  SettingsPage,
  TemplatesPage,
} from "../routes/app-pages";
import {
  AdminQueuePage,
  AdminRendersPage,
  AdminWorkspacesPage,
} from "../routes/admin-pages";

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
        path: "settings",
        element: <SettingsPage />,
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
