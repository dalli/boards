// Minimal API client. Access token is held IN MEMORY ONLY (S-01) — never in
// localStorage/sessionStorage — to limit XSS token theft. Refresh requires re-login.

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${BASE_URL}${path}`, { ...init, headers });
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function toError(resp: Response): Promise<ApiError> {
  let detail = resp.statusText;
  try {
    const body = await resp.json();
    if (body && typeof body.detail === "string") detail = body.detail;
  } catch {
    // non-JSON body; keep statusText
  }
  return new ApiError(resp.status, detail);
}

/** JSON request returning parsed body, throwing ApiError on non-2xx. */
export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const resp = await apiFetch(path, init);
  if (!resp.ok) throw await toError(resp);
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

/** Multipart request (FormData) returning parsed body, throwing ApiError on non-2xx. */
export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  const resp = await apiFetch(path, { method: "POST", body: form });
  if (!resp.ok) throw await toError(resp);
  return (await resp.json()) as T;
}
