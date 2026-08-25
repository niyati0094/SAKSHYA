import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  UNAUTHORIZED_EVENT,
  apiFetch,
  clearToken,
  getToken,
  setToken,
} from '../api/client';

function mockResponse(body: unknown, init: { status?: number } = {}) {
  const status = init.status ?? 200;
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('stores and clears the token', () => {
    setToken('abc');
    expect(getToken()).toBe('abc');
    clearToken();
    expect(getToken()).toBeNull();
  });

  it('attaches the bearer token when one is stored', async () => {
    setToken('token-123');
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/me/pathway');

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer token-123');
  });

  it('prefixes requests with the versioned api path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({}));
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/health');

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/health');
  });

  it('surfaces the server detail message on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(mockResponse({ detail: 'Competency not found' }, { status: 404 })),
    );

    await expect(apiFetch('/me/competencies/999')).rejects.toThrowError(
      new ApiError(404, 'Competency not found'),
    );
  });

  it('reports an unreachable backend rather than a generic failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')));

    await expect(apiFetch('/health')).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining('Cannot reach the SAKSHYA backend'),
    });
  });

  it('clears the session and signals when the token is rejected', async () => {
    setToken('stale');
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse({}, { status: 401 })));

    await expect(apiFetch('/me/pathway')).rejects.toBeInstanceOf(ApiError);

    expect(getToken()).toBeNull();
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  });

  it('does not end the session when a login attempt is rejected', async () => {
    // A 401 on login is a wrong password, not an expired session.
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(mockResponse({ detail: 'Incorrect email or password' }, { status: 401 })),
    );

    await expect(
      apiFetch('/auth/login', { method: 'POST', body: '{}' }),
    ).rejects.toBeInstanceOf(ApiError);

    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  });
});
