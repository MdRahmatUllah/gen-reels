import type { GenerationStatus } from "../types/domain";

const statusLabels: Record<GenerationStatus, string> = {
  idle: "Ready",
  queued: "Queued…",
  running: "Generating…",
  completed: "Complete",
  failed: "Failed",
};

const statusClasses: Record<GenerationStatus, string> = {
  idle: "status-badge status-badge--neutral",
  queued: "status-badge status-badge--warning",
  running: "status-badge status-badge--primary",
  completed: "status-badge status-badge--success",
  failed: "status-badge status-badge--error",
};

export function GenerationStatusIndicator({
  status,
  label,
}: {
  status: GenerationStatus;
  label?: string;
}) {
  return (
    <div className="generation-status">
      {status === "running" ? (
        <div className="generation-status__spinner" aria-hidden="true" />
      ) : null}
      <span className={statusClasses[status]}>
        {label ?? statusLabels[status]}
      </span>
    </div>
  );
}
