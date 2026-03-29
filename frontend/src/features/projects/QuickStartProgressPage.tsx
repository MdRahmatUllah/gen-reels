import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { LoadingPage, MetricCard, PageFrame, SectionCard, StatusBadge } from "../../components/ui";
import { useQuickCreateStatus } from "../../hooks/use-projects";
import { QuickStartStatusBanner, quickStartLabel } from "./quick-start";

export function QuickStartProgressPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "" } = useParams();
  const { data: status, isLoading, error } = useQuickCreateStatus(projectId);

  useEffect(() => {
    if (!status) {
      return;
    }
    if (status.isCompleted || status.hasFailed) {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-bundle", projectId] });
      queryClient.invalidateQueries({ queryKey: ["brief", projectId] });
      queryClient.invalidateQueries({ queryKey: ["ideas", projectId] });
      queryClient.invalidateQueries({ queryKey: ["script", projectId] });
      queryClient.invalidateQueries({ queryKey: ["scenePlan", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    }
    if (status.isCompleted) {
      const timeout = window.setTimeout(() => {
        navigate(status.redirectPath, { replace: true });
      }, 900);
      return () => window.clearTimeout(timeout);
    }
    return undefined;
  }, [navigate, projectId, queryClient, status]);

  if (isLoading) {
    return <LoadingPage />;
  }

  if (!status) {
    return (
      <PageFrame
        eyebrow="Project bootstrap"
        title="Quick-start unavailable"
        description="No quick-start bootstrap state was found for this project."
        inspector={<div className="inspector-stack" />}
      >
        <SectionCard title="Recovery">
          <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
            Open the project directly, or start a new quick-create flow from the Projects page.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
              to={`/app/projects/${projectId}/brief`}
            >
              Open project
            </Link>
            <Link
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
              to="/app/projects"
            >
              Back to projects
            </Link>
          </div>
          {error instanceof Error ? (
            <p className="text-[0.82rem] text-secondary">{error.message}</p>
          ) : null}
        </SectionCard>
      </PageFrame>
    );
  }

  return (
    <PageFrame
      eyebrow="Project bootstrap"
      title={status.projectTitle}
      description="The platform is synthesizing the brief, selecting the top idea, generating the script, and approving the scene plan before handing you off to production review."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Progress facts">
            <div className="inspector-list">
              <div>
                <span>Status</span>
                <strong>
                  <StatusBadge status={status.job.status} />
                </strong>
              </div>
              <div>
                <span>Current step</span>
                <strong>{quickStartLabel(status.currentStep)}</strong>
              </div>
              <div>
                <span>Completed</span>
                <strong>
                  {status.completedSteps.length} / {status.steps.length}
                </strong>
              </div>
              <div>
                <span>Project stage</span>
                <strong>{status.projectStage}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <QuickStartStatusBanner status={status} />

      <div className="metric-grid">
        <MetricCard
          label="Current step"
          value={quickStartLabel(status.currentStep)}
          detail="The background orchestrator continues even if you close this tab."
          tone={status.hasFailed ? "error" : status.isCompleted ? "success" : "primary"}
        />
        <MetricCard
          label="Approved endpoint"
          value={status.isCompleted ? "Scenes ready" : "Scene plan pending"}
          detail="Quick-start stops before render generation."
          tone={status.isCompleted ? "success" : "neutral"}
        />
      </div>

      <SectionCard
        title={status.hasFailed ? "Bootstrap stopped" : status.isCompleted ? "Redirecting..." : "Execution steps"}
        subtitle={
          status.hasFailed
            ? "Review the failing step and jump back into the workflow at the last safe page."
            : status.isCompleted
              ? "You will be redirected to the Scene Planner automatically."
              : "Each step runs in order on the backend and updates here as it finishes."
        }
      >
        <div className="flex flex-col gap-3">
          {status.steps.map((step) => (
            <div
              key={step.stepKind}
              className="flex flex-col gap-2 rounded-xl border border-border-card bg-glass px-4 py-3 md:flex-row md:items-center md:justify-between"
            >
              <div className="flex flex-col gap-1">
                <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">
                  Step {step.stepIndex}
                </p>
                <strong className="text-primary">{quickStartLabel(step.stepKind)}</strong>
                {step.errorMessage ? (
                  <p className="text-sm text-error">{step.errorMessage}</p>
                ) : (
                  <p className="text-sm text-secondary">
                    {step.completedAt
                      ? `Completed at ${new Date(step.completedAt).toLocaleTimeString()}`
                      : step.startedAt
                        ? "Running in the background"
                        : "Waiting for its turn"}
                  </p>
                )}
              </div>
              <StatusBadge status={step.status} />
            </div>
          ))}
        </div>

        {status.hasFailed ? (
          <div className="flex flex-wrap items-center gap-2">
            <Link
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
              to={status.recoveryPath}
            >
              Open recovery page
            </Link>
            <Link
              className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
              to="/app/projects"
            >
              Back to projects
            </Link>
          </div>
        ) : null}
      </SectionCard>
    </PageFrame>
  );
}
