import { config, isMockMode } from "./config";

/* ─── Error types ─────────────────────────────────────────────────────────── */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/* ─── Core fetch wrapper ──────────────────────────────────────────────────── */
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  if (isMockMode()) {
    // In mock mode, the mock service intercepts calls via the hooks layer.
    // This function should never be called directly in mock mode.
    throw new Error(`api-client.request called in mock mode for ${method} ${path}`);
  }

  const url = `${config.apiBaseUrl}/api/v1${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const response = await fetch(url, {
    method,
    headers,
    credentials: "include", // HttpOnly cookies for auth
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorBody.code ?? "unknown_error",
      errorBody.message ?? response.statusText,
      errorBody.details,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/* ─── Public API methods ──────────────────────────────────────────────────── */
export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
} as const;
