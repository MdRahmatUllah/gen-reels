import type { ReactNode } from "react";

import { EmptyState, SectionCard, StatusBadge } from "../../components/ui";
import { isMockMode } from "../../lib/config";

export function PublishingLiveModeNotice() {
  if (!isMockMode()) {
    return null;
  }
  return (
    <SectionCard
      title="Live API Required"
      subtitle="These publishing screens call the backend directly and are intentionally disabled in mock mode."
    >
      <p className="text-sm leading-6 text-secondary">
        Set <code>VITE_API_MODE=live</code> and point <code>VITE_API_URL</code> at your FastAPI backend to use
        YouTube connections, scheduling, and uploads.
      </p>
    </SectionCard>
  );
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Not set";
  }
  return new Date(value).toLocaleString();
}

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatDurationMs(durationMs: number | null | undefined): string {
  if (!durationMs || durationMs <= 0) {
    return "Unknown";
  }
  const totalSeconds = Math.round(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function PublishingMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-xl border border-border-card bg-card p-4">
      <p className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">{label}</p>
      <strong className="mt-2 block text-2xl font-heading font-bold text-primary">{value}</strong>
      <p className="mt-1 text-sm text-secondary">{detail}</p>
    </div>
  );
}

export function PublishingEmptyState({ title, description }: { title: string; description: string }) {
  return <EmptyState title={title} description={description} />;
}

export function DetailPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-glass px-3 py-1 text-xs font-medium text-secondary">
      {children}
    </span>
  );
}

export { StatusBadge };
