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

/* ─── Silent token refresh ────────────────────────────────────────────────── */
let refreshInFlight: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${config.apiBaseUrl}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/* ─── Core fetch wrapper ──────────────────────────────────────────────────── */
interface RequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
}

async function rawFetch(
  method: string,
  url: string,
  headers: Record<string, string>,
  body: string | undefined,
): Promise<Response> {
  return fetch(url, { method, headers, credentials: "include", body });
}

async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  if (isMockMode()) {
    throw new Error(`api-client.request called in mock mode for ${method} ${path}`);
  }

  const url = `${config.apiBaseUrl}/api/v1${path}`;

  const headers: Record<string, string> = {
    ...options.headers,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }

  const serializedBody = options.body !== undefined ? JSON.stringify(options.body) : undefined;

  let response = await rawFetch(method, url, headers, serializedBody);

  // On 401, silently refresh tokens and retry once (skip for auth endpoints).
  if (response.status === 401 && !path.startsWith("/auth/")) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      response = await rawFetch(method, url, headers, serializedBody);
    }
  }

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
