function envFlag(value: string | undefined): boolean | undefined {
  if (!value) return undefined;
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return undefined;
}

export const config = {
  apiBaseUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  apiMode: (import.meta.env.VITE_API_MODE ?? "mock") as "mock" | "live",
  disableBrowserAuth: envFlag(import.meta.env.VITE_DISABLE_BROWSER_AUTH) ?? import.meta.env.DEV,
} as const;

export function isMockMode(): boolean {
  return config.apiMode === "mock";
}
