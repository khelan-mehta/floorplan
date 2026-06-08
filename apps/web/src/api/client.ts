import type { Boundary, Plan, ProgramGraph } from '@fpg/schemas';
import type {
  CodeQueryResponse,
  DiffOut,
  JobOut,
  PlanOut,
  ProblemDetails,
  ProjectOut,
  RuleSetSummary,
  TokenResponse,
  UserOut,
} from './types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const TOKEN_KEY = 'fpg.tokens';

export function loadTokens(): TokenResponse | null {
  const raw = localStorage.getItem(TOKEN_KEY);
  return raw ? (JSON.parse(raw) as TokenResponse) : null;
}

export function saveTokens(tokens: TokenResponse | null): void {
  if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public problem: ProblemDetails | null,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const tokens = loadTokens();
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (tokens) headers['Authorization'] = `Bearer ${tokens.access_token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const problem = (data ?? null) as ProblemDetails | null;
    throw new ApiError(res.status, problem, problem?.title ?? `HTTP ${res.status}`);
  }
  return data as T;
}

export const api = {
  baseUrl: API_BASE_URL,

  // auth
  register: (b: { email: string; password: string; name: string; org_name?: string }) =>
    request<TokenResponse>('POST', '/auth/register', b),
  login: (b: { email: string; password: string }) =>
    request<TokenResponse>('POST', '/auth/login', b),
  refresh: (refresh_token: string) =>
    request<TokenResponse>('POST', '/auth/refresh', { refresh_token }),
  me: () => request<UserOut>('GET', '/auth/me'),

  // projects
  listProjects: () => request<ProjectOut[]>('GET', '/projects'),
  createProject: (b: { name: string; units?: string; jurisdiction_id?: string }) =>
    request<ProjectOut>('POST', '/projects', b),
  getProject: (id: string) => request<ProjectOut>('GET', `/projects/${id}`),
  updateProject: (id: string, b: Partial<{ name: string; units: string }>) =>
    request<ProjectOut>('PATCH', `/projects/${id}`, b),

  // boundary / program
  getBoundary: (id: string) =>
    request<{ id: string; doc: Boundary }>('GET', `/projects/${id}/boundary`),
  putBoundary: (id: string, doc: Boundary) =>
    request<{ id: string; doc: Boundary }>('PUT', `/projects/${id}/boundary`, doc),
  getProgram: (id: string) =>
    request<{ id: string; doc: ProgramGraph }>('GET', `/projects/${id}/program`),
  putProgram: (id: string, doc: ProgramGraph) =>
    request<{ id: string; doc: ProgramGraph }>('PUT', `/projects/${id}/program`, doc),

  // plans
  listPlans: (id: string) => request<PlanOut[]>('GET', `/projects/${id}/plans`),
  getPlan: (planId: string) => request<PlanOut>('GET', `/plans/${planId}`),
  patchPlan: (planId: string, patch: Partial<Plan>, source = 'edited') =>
    request<PlanOut>('PATCH', `/plans/${planId}`, { patch, source }),
  duplicatePlan: (planId: string) => request<PlanOut>('POST', `/plans/${planId}/duplicate`),
  planVersions: (planId: string) => request<PlanOut[]>('GET', `/plans/${planId}/versions`),
  diffPlans: (a: string, b: string) => request<DiffOut>('GET', `/plans/${a}/diff/${b}`),

  // jobs
  generate: (id: string, b: { count?: number; seed?: number }) =>
    request<JobOut>('POST', `/projects/${id}/generate`, b),
  getJob: (jobId: string) => request<JobOut>('GET', `/jobs/${jobId}`),

  // building codes (Phase 07)
  listCodes: () => request<RuleSetSummary[]>('GET', '/codes'),
  queryCodes: (b: { jurisdiction_id: string; query: string; top_k?: number }) =>
    request<CodeQueryResponse>('POST', '/codes/query', b),
  uploadCode: (b: {
    jurisdiction_id: string;
    jurisdiction_name?: string;
    doc_title: string;
    text: string;
    version?: string;
  }) => request<{ ruleset: { rule_count: number }; chunks: number }>('POST', '/codes/upload', b),

  // export (binary)
  exportPlan: async (planId: string, format: 'dxf' | 'ifc' | 'csv'): Promise<Blob> => {
    const tokens = loadTokens();
    const res = await fetch(`${API_BASE_URL}/plans/${planId}/export?format=${format}`, {
      method: 'POST',
      headers: tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, null, `Export failed (${res.status})`);
    return res.blob();
  },
};

export function jobWebsocketUrl(jobId: string): string {
  const tokens = loadTokens();
  const wsBase = API_BASE_URL.replace(/^http/, 'ws');
  const token = tokens ? `?token=${encodeURIComponent(tokens.access_token)}` : '';
  return `${wsBase}/ws/jobs/${jobId}${token}`;
}
