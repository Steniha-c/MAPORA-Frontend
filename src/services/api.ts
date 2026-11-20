import type {
  AdminAnalytics,
  AuthSession,
  FloorPlanModel,
  ImageUploadItem,
  MapProject,
  ProcessingStatus,
  ProjectVersion,
} from '../types';

export const API_BASE = import.meta.env.VITE_MAPORA_API_BASE?.replace(/\/$/, '') ?? '';
export const isApiConfigured = Boolean(API_BASE);

export const AUTH_STORAGE_KEY = 'mapora_auth_session';

export class ApiUnavailableError extends Error {
  constructor(message = 'The MAPORA backend is not configured in this repository yet.') {
    super(message);
    this.name = 'ApiUnavailableError';
  }
}

/**
 * Safely parse and retrieve the stored auth session from localStorage.
 */
export function getStoredSession(): AuthSession | null {
  try {
    const saved = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved) as AuthSession;
    if (parsed?.accessToken && parsed?.user?.id) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Persist or clear the auth session in localStorage.
 */
export function storeSession(session: AuthSession | null): void {
  try {
    if (session) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch {
    /* Ignore storage write errors */
  }
}

/**
 * Safely decode base64url-encoded JWT payload without external library.
 */
export function decodeJwtPayload(token: string): { exp?: number; sub?: string; role?: string; email?: string; type?: string } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * Check if a JWT access token has expired or is about to expire within buffer window.
 */
export function isTokenExpired(token?: string | null, skewSeconds = 30): boolean {
  if (!token) return true;
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return false;
  const nowSeconds = Math.floor(Date.now() / 1000);
  return payload.exp <= nowSeconds + skewSeconds;
}

/**
 * Broadcast session expiration and wipe stored credentials.
 */
export function notifySessionExpired(message = 'Your session has expired. Please sign in again.') {
  storeSession(null);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('mapora:session-expired', { detail: { message } }));
  }
}

// Single-flight refresh promise to prevent stampeding concurrent refresh calls
let activeRefreshPromise: Promise<string | null> | null = null;

/**
 * Exchange the stored refresh token for a fresh access token.
 * Retries are deduplicated across all active callers.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (activeRefreshPromise) {
    return activeRefreshPromise;
  }

  activeRefreshPromise = (async () => {
    const session = getStoredSession();
    const refreshToken = session?.refreshToken;
    if (!refreshToken || !API_BASE) {
      notifySessionExpired();
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });

      if (!response.ok) {
        notifySessionExpired();
        return null;
      }

      const data = (await response.json()) as {
        accessToken?: string;
        access_token?: string;
        refreshToken?: string;
        refresh_token?: string;
        token_type?: string;
        user?: { id: string; email: string; role: 'admin' | 'surveyor' };
      };

      const newAccessToken = data.accessToken || data.access_token;
      if (!newAccessToken) {
        notifySessionExpired();
        return null;
      }

      const updatedSession: AuthSession = {
        accessToken: newAccessToken,
        refreshToken: data.refreshToken || data.refresh_token || refreshToken,
        tokenType: data.token_type || 'bearer',
        user: data.user || session.user,
      };

      storeSession(updatedSession);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('mapora:session-refreshed', { detail: updatedSession }));
      }
      return updatedSession.accessToken;
    } catch {
      notifySessionExpired();
      return null;
    } finally {
      activeRefreshPromise = null;
    }
  })();

  return activeRefreshPromise;
}

/**
 * Retrieve a valid, unexpired access token, automatically refreshing if needed.
 */
export async function getValidAccessToken(preferredToken?: string): Promise<string | null> {
  const currentToken = preferredToken || getStoredSession()?.accessToken;
  if (!currentToken) return null;

  if (!isTokenExpired(currentToken)) {
    return currentToken;
  }

  // Token is expired; attempt controlled refresh
  return await refreshAccessToken();
}

/**
 * Generic fetch wrapper with automatic JWT injection, timeout, and 401 refresh recovery.
 */
async function request<T>(
  path: string,
  init?: RequestInit,
  token?: string,
  timeoutMs = 15000,
  isRetry = false,
): Promise<T> {
  if (!API_BASE) throw new ApiUnavailableError();

  const isAuthEndpoint = path.startsWith('/auth/login') || path.startsWith('/auth/refresh') || path.startsWith('/auth/register');

  let activeToken = token || getStoredSession()?.accessToken;

  // Preemptively refresh expired token before protected requests
  if (!isAuthEndpoint && activeToken && isTokenExpired(activeToken)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      activeToken = refreshed;
    }
  }

  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (activeToken) {
    headers.set('Authorization', `Bearer ${activeToken}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort(new Error(`MAPORA API request to ${path} timed out after ${timeoutMs}ms.`));
  }, timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      signal: init?.signal || controller.signal,
    });
  } catch (cause: unknown) {
    if (cause instanceof Error) {
      if (cause.name === 'AbortError' || cause.message.includes('timed out')) {
        throw new Error(`The MAPORA backend at ${API_BASE} timed out. Please verify that the server is responding.`);
      }
      if (cause.message.toLowerCase().includes('failed to fetch')) {
        throw new Error(`Cannot connect to MAPORA backend at ${API_BASE}. Please ensure the backend server is running.`);
      }
    }
    throw cause;
  } finally {
    clearTimeout(timeoutId);
  }

  // Handle 401 Unauthorized with automatic single-retry token refresh
  if (response.status === 401 && !isAuthEndpoint && !isRetry) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      // Retry the original request with the fresh token
      return request<T>(path, init, refreshedToken, timeoutMs, true);
    }
    notifySessionExpired('Your session has expired. Please sign in again.');
    throw new Error('Your session has expired. Please sign in again.');
  }

  if (!response.ok) {
    let detail = '';
    try {
      const body = (await response.json()) as {
        message?: string;
        error?: string;
        detail?: string | Array<{ msg?: string }>;
      };
      if (typeof body.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        detail = body.detail[0].msg;
      } else {
        detail = body.message || body.error || '';
      }
    } catch {
      /* A non-JSON error body is not required */
    }

    if (response.status === 401 && !isAuthEndpoint) {
      notifySessionExpired('Your session has expired. Please sign in again.');
      throw new Error('Your session has expired. Please sign in again.');
    }

    throw new Error(detail || `MAPORA API request failed (${response.status}).`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const maporaApi = {
  login: async (email: string, password: string) => {
    const session = await request<AuthSession>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (session?.accessToken) {
      storeSession(session);
    }
    return session;
  },

  refreshSession: (refreshToken: string) =>
    request<AuthSession>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refreshToken }),
    }),

  logout: async (refreshToken?: string, token?: string) => {
    try {
      await request<{ message: string }>(
        '/auth/logout',
        {
          method: 'POST',
          body: JSON.stringify({ refreshToken }),
        },
        token,
      );
    } catch {
      /* Ignore remote logout failure during teardown */
    } finally {
      storeSession(null);
    }
  },

  listProjects: (token?: string) => request<MapProject[]>('/projects', undefined, token),
  getProject: (projectId: string, token?: string) =>
    request<MapProject>(`/projects/${encodeURIComponent(projectId)}`, undefined, token),

  createMapping: (video: File, token?: string) => {
    const body = new FormData();
    body.append('video', video);
    return request<{ id: string; status: string }>('/projects', { method: 'POST', body }, token, 300000);
  },

  createPhotoMapping: (images: File[], name?: string, token?: string) => {
    const body = new FormData();
    if (name) body.append('name', name);
    for (const img of images) {
      body.append('images', img);
    }
    return request<{ id: string; status: string }>('/projects', { method: 'POST', body }, token, 300000);
  },

  uploadProjectImages: (projectId: string, images: File[], token?: string) => {
    const body = new FormData();
    for (const img of images) {
      body.append('files', img);
    }
    return request<{ uploaded: number; images: ImageUploadItem[]; projectId: string }>(
      `/projects/${encodeURIComponent(projectId)}/images`,
      { method: 'POST', body },
      token,
      300000,
    );
  },

  getProjectImages: (projectId: string, token?: string) =>
    request<ImageUploadItem[]>(`/projects/${encodeURIComponent(projectId)}/images`, undefined, token),

  triggerImageReconstruction: (projectId: string, token?: string) =>
    request<ProcessingStatus>(`/projects/${encodeURIComponent(projectId)}/reconstruct/images`, { method: 'POST' }, token),

  renameProject: (projectId: string, name: string, token?: string) =>
    request<MapProject>(
      `/projects/${encodeURIComponent(projectId)}`,
      { method: 'PATCH', body: JSON.stringify({ name }) },
      token,
    ),

  deleteProject: (projectId: string, token?: string) =>
    request<void>(`/projects/${encodeURIComponent(projectId)}`, { method: 'DELETE' }, token),

  getProjectVersions: (projectId: string, token?: string) =>
    request<ProjectVersion[]>(`/projects/${encodeURIComponent(projectId)}/versions`, undefined, token),

  createProjectVersion: (projectId: string, token?: string) =>
    request<ProjectVersion>(`/projects/${encodeURIComponent(projectId)}/versions`, { method: 'POST' }, token),

  restoreProjectVersion: (projectId: string, versionId: string, token?: string) =>
    request<void>(
      `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/restore`,
      { method: 'POST' },
      token,
    ),

  getProcessingStatus: (projectId: string, token?: string) =>
    request<ProcessingStatus>(`/projects/${encodeURIComponent(projectId)}/status`, undefined, token),

  retryProcessing: (projectId: string, token?: string) =>
    request<ProcessingStatus>(`/projects/${encodeURIComponent(projectId)}/retry`, { method: 'POST' }, token),

  getFloorPlan: (projectId: string, token?: string) =>
    request<FloorPlanModel>(`/projects/${encodeURIComponent(projectId)}/floor-plan`, undefined, token),

  updateFloorPlan: (
    projectId: string,
    update: { rooms?: Array<{ id: string; name?: string; bounds?: { x: number; y: number; width: number; height: number }; areaSquareMeters?: number }> },
    token?: string,
  ) =>
    request<FloorPlanModel>(
      `/projects/${encodeURIComponent(projectId)}/floor-plan`,
      { method: 'PATCH', body: JSON.stringify(update) },
      token,
    ),

  getScene: (projectId: string, token?: string) =>
    request<{ geometryUrl: string }>(`/projects/${encodeURIComponent(projectId)}/scene`, undefined, token),

  getAdminAnalytics: (token?: string) => request<AdminAnalytics>('/admin/analytics', undefined, token),

  downloadExport: async (projectId: string, format: 'svg' | 'dxf' | 'pdf' | 'obj' | 'gltf' | 'glb', token?: string) => {
    if (!API_BASE) throw new ApiUnavailableError();
    const validToken = await getValidAccessToken(token);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    try {
      const headers: Record<string, string> = {};
      if (validToken) {
        headers['Authorization'] = `Bearer ${validToken}`;
      }
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/export?format=${format}`, {
        headers,
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Export request failed (${response.status}).`);
      return await response.blob();
    } catch (cause: unknown) {
      if (cause instanceof Error && cause.name === 'AbortError') {
        throw new Error('Export download timed out.');
      }
      throw cause;
    } finally {
      clearTimeout(timeoutId);
    }
  },
};
