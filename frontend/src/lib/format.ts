export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;

  if (minutes === 0) {
    return `${remainder}s`;
  }

  return `${minutes}m ${remainder}s`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatSignedSeconds(value: number): string {
  if (value === 0) {
    return "0.0s";
  }

  return `${value > 0 ? "+" : ""}${value.toFixed(1)}s`;
}

export function titleFromStatus(value: string): string {
  return value.replace(/_/g, " ");
}
