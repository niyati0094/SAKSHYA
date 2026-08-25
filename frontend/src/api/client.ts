const TOKEN_KEY = 'sakshya.token';

/** Fired when the API rejects our token, so the session can be torn down. */
export const UNAUTHORIZED_EVENT = 'sakshya:unauthorized';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');

  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers });
  } catch {
    // Network-level failure: the backend is not reachable at all.
    throw new ApiError(0, 'Cannot reach the SAKSHYA backend. Is the API server running?');
  }

  // A rejected token means the session is over. Clear it and let the app fall
  // back to the login screen rather than leaving the user on a page that can
  // only render an error. The login endpoint is exempt: a 401 there is a wrong
  // password, not an expired session.
  if (response.status === 401 && path !== '/auth/login') {
    clearToken();
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') {
        detail = body.detail;
      }
    } catch {
      // Response body was not JSON; keep the generic message.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
