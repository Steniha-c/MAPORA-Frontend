import type { AdminAnalytics, AuthSession, FloorPlanModel, MapProject, ProcessingStatus, ProjectVersion } from '../types';

export const API_BASE = import.meta.env.VITE_MAPORA_API_BASE?.replace(/\/$/, '') ?? '';
export const isApiConfigured = Boolean(API_BASE);

export class ApiUnavailableError extends Error {
  constructor(message = 'The MAPORA backend is not configured in this repository yet.') {
    super(message);
    this.name = 'ApiUnavailableError';
  }
}

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  if (!API_BASE) throw new ApiUnavailableError();
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json() as { message?: string; error?: string };
      detail = body.message || body.error || '';
    } catch { /* A non-JSON error body is not required. */ }
    throw new Error(detail || `MAPORA API request failed (${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const maporaApi = {
  login: (email: string, password: string) => request<AuthSession>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  listProjects: (token?: string) => request<MapProject[]>('/projects', undefined, token),
  getProject: (projectId: string, token?: string) => request<MapProject>(`/projects/${encodeURIComponent(projectId)}`, undefined, token),
  createMapping: (video: File, token?: string) => {
    const body = new FormData();
    body.append('video', video);
    return request<{ id: string; status: string }>('/projects', { method: 'POST', body }, token);
  },
  renameProject: (projectId: string, name: string, token: string) => request<MapProject>(`/projects/${encodeURIComponent(projectId)}`, { method: 'PATCH', body: JSON.stringify({ name }) }, token),
  deleteProject: (projectId: string, token: string) => request<void>(`/projects/${encodeURIComponent(projectId)}`, { method: 'DELETE' }, token),
  getProjectVersions: (projectId: string, token?: string) => request<ProjectVersion[]>(`/projects/${encodeURIComponent(projectId)}/versions`, undefined, token),
  createProjectVersion: (projectId: string, token: string) => request<ProjectVersion>(`/projects/${encodeURIComponent(projectId)}/versions`, { method: 'POST' }, token),
  restoreProjectVersion: (projectId: string, versionId: string, token: string) => request<void>(`/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/restore`, { method: 'POST' }, token),
  getProcessingStatus: (projectId: string, token?: string) => request<ProcessingStatus>(`/projects/${encodeURIComponent(projectId)}/status`, undefined, token),
  retryProcessing: (projectId: string, token?: string) => request<ProcessingStatus>(`/projects/${encodeURIComponent(projectId)}/retry`, { method: 'POST' }, token),
  getFloorPlan: (projectId: string, token?: string) => request<FloorPlanModel>(`/projects/${encodeURIComponent(projectId)}/floor-plan`, undefined, token),
  getScene: (projectId: string, token?: string) => request<{ geometryUrl: string }>(`/projects/${encodeURIComponent(projectId)}/scene`, undefined, token),
  getAdminAnalytics: (token: string) => request<AdminAnalytics>('/admin/analytics', undefined, token),
  downloadExport: async (projectId: string, format: 'svg' | 'dxf' | 'pdf' | 'obj' | 'gltf' | 'glb', token: string) => {
    if (!API_BASE) throw new ApiUnavailableError();
    const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/export?format=${format}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error(`Export request failed (${response.status}).`);
    return response.blob();
  },
};
