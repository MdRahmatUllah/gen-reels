export const config = {
  apiBaseUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  apiMode: (import.meta.env.VITE_API_MODE ?? "mock") as "mock" | "live",
} as const;

export function isMockMode(): boolean {
  return config.apiMode === "mock";
}
