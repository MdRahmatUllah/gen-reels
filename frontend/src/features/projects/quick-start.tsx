import { Link } from "react-router-dom";

import { ProgressBar, StatusBadge } from "../../components/ui";
import type { QuickCreateStatus, QuickCreateStepStatus } from "../../types/domain";

const quickStartLabels: Record<string, string> = {
  brief_generation: "Brief",
  idea_generation: "Ideas",
  script_generation: "Script",
  scene_plan_generation: "Scene Plan",
  prompt_pair_generation: "Prompt Pairs",
};

export function quickStartLabel(stepKind: string | null | undefined): string {
  if (!stepKind) {
    return "Preparing";
  }
  return quickStartLabels[stepKind] ?? stepKind.replace(/[_-]+/g, " ");
}

function stepChipClass(status: QuickCreateStepStatus["status"]): string {
  if (status === "completed") {
    return "bg-success-bg text-success border-success-glow";
  }
  if (status === "running") {
    return "bg-primary-bg text-primary-fg border-border-active";
  }
  if (status === "failed") {
    return "bg-error-bg text-error border-error-bg";
  }
  return "bg-glass text-secondary border-border-subtle";
}

export function QuickStartStatusBanner({
  status,
  compact = false,
}: {
  status: QuickCreateStatus;
  compact?: boolean;
}) {
  const completedCount = status.completedSteps.length;
  const totalSteps = Math.max(1, status.steps.length);
  const progressValue = (completedCount / totalSteps) * 100;
  const heading = status.hasFailed
    ? "Quick-start needs attention"
    : status.isCompleted
      ? "Quick-start complete"
      : "Quick-start is building this project";
  const detail = status.hasFailed
    ? status.job.errorMessage ?? `The ${quickStartLabel(status.currentStep)} step needs review.`
    : status.isCompleted
      ? "Everything is ready through the approved scene plan."
      : `${quickStartLabel(status.currentStep)} is running. The rest of the workflow will unlock automatically.`;

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-border-active bg-card p-5 shadow-card animate-rise-in">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="flex flex-col gap-1">
          <p className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted">
            Project Bootstrap
          </p>
          <h3 className="font-heading text-[1.1rem] font-bold text-primary">{heading}</h3>
          <p className="text-[0.9rem] leading-[1.6] text-secondary">{detail}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={status.job.status} />
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.2rem] px-3 py-1.5 rounded-md font-semibold text-xs transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
            to={`/app/projects/${status.projectId}/quick-start`}
          >
            Open progress
          </Link>
        </div>
      </div>

      <ProgressBar
        value={progressValue}
        label="Completed steps"
        detail={`${completedCount} of ${totalSteps} finished${status.currentStep ? `, currently on ${quickStartLabel(status.currentStep)}` : ""}.`}
      />

      <div className="flex flex-wrap items-center gap-2">
        {status.steps.map((step) => (
          <span
            key={step.stepKind}
            className={`inline-flex items-center rounded-full border px-3 py-1 text-[0.72rem] font-semibold uppercase tracking-[0.12em] ${stepChipClass(step.status)}`}
          >
            {quickStartLabel(step.stepKind)}
          </span>
        ))}
      </div>

      {!compact && status.hasFailed ? (
        <div className="flex flex-wrap items-center gap-2">
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.5rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
            to={status.recoveryPath}
          >
            Open recovery step
          </Link>
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.5rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
            to={`/app/projects/${status.projectId}/brief`}
          >
            Open project
          </Link>
        </div>
      ) : null}
    </section>
  );
}
