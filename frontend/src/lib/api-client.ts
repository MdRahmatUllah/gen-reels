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
interface RequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
}

async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  if (isMockMode()) {
    // In mock mode, the mock service intercepts calls via the hooks layer.
    // This function should never be called directly in mock mode.
    throw new Error(`api-client.request called in mock mode for ${method} ${path}`);
  }

  const url = `${config.apiBaseUrl}/api/v1${path}`;

  const headers: Record<string, string> = {
    ...options.headers,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }

  const response = await fetch(url, {
    method,
    headers,
    credentials: "include", // HttpOnly cookies for auth
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const normalizedError = errorBody.error ?? errorBody;
    throw new ApiError(
      response.status,
      normalizedError.code ?? "unknown_error",
      normalizedError.message ?? response.statusText,
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
  get: <T>(path: string, headers?: Record<string, string>) => request<T>("GET", path, { headers }),
  post: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>("POST", path, { body, headers }),
  patch: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>("PATCH", path, { body, headers }),
  put: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>("PUT", path, { body, headers }),
  delete: <T>(path: string, headers?: Record<string, string>) => request<T>("DELETE", path, { headers }),
} as const;
