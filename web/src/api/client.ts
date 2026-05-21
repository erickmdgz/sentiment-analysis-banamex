import type { ErrorResponse } from './schema';

export const TOKEN_KEY = 'banamex_token';

export class ApiError extends Error {
  public status: number;
  public code: string;
  public hint?: string;

  constructor(status: number, body: Partial<ErrorResponse>) {
    super(body.detail ?? `HTTP ${status}`);
    this.status = status;
    this.code = body.code ?? 'http_error';
    this.hint = body.hint;
  }
}

interface RequestOptions {
  method?: string;
  body?: BodyInit | null;
  headers?: HeadersInit;
  signal?: AbortSignal;
  isFormData?: boolean;
}

function baseUrl(): string {
  // Cuando MSW está activo (VITE_USE_MOCKS=true), Vite intercepta cualquier
  // URL same-origin, así que mantenemos VITE_API_URL como prefijo opcional.
  if (import.meta.env.VITE_USE_MOCKS === 'true') return '';
  return import.meta.env.VITE_API_URL ?? '';
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (!opts.isFormData && opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${baseUrl()}${path}`, {
    method: opts.method ?? 'GET',
    body: opts.body,
    headers,
    signal: opts.signal,
  });

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    throw new ApiError(401, { detail: 'Sesión expirada', code: 'unauthorized' });
  }

  if (!res.ok) {
    let body: Partial<ErrorResponse> = {};
    try {
      body = (await res.json()) as Partial<ErrorResponse>;
    } catch {
      body = { detail: `Error HTTP ${res.status}` };
    }
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const apiClient = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: 'POST', body: form, isFormData: true }),
};
