import { describe, expect, it, beforeAll, afterAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { ApiError, TOKEN_KEY, apiClient } from '@/api/client';

const server = setupServer(
  http.get('http://localhost/echo-auth', ({ request }) => {
    return HttpResponse.json({ auth: request.headers.get('Authorization') ?? null });
  }),
  http.get('http://localhost/expired', () =>
    HttpResponse.json({ detail: 'no auth', code: 'unauthorized' }, { status: 401 }),
  ),
  http.get('http://localhost/teapot', () =>
    HttpResponse.json({ detail: 'no soy una tetera', code: 'teapot' }, { status: 418 }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterAll(() => server.close());
beforeEach(() => {
  localStorage.clear();
});

describe('apiClient', () => {
  it('añade Authorization: Bearer <token> cuando hay token', async () => {
    localStorage.setItem(TOKEN_KEY, 'tok-abc');
    const res = await apiClient.get<{ auth: string }>('/echo-auth');
    expect(res.auth).toBe('Bearer tok-abc');
  });

  it('borra el token cuando recibe 401 y lanza ApiError', async () => {
    localStorage.setItem(TOKEN_KEY, 'will-be-cleared');
    await expect(apiClient.get('/expired')).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it('propaga ApiError con status y code para otros 4xx', async () => {
    localStorage.setItem(TOKEN_KEY, 'tok');
    try {
      await apiClient.get('/teapot');
      throw new Error('debería haber lanzado');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(418);
      expect(apiErr.code).toBe('teapot');
    }
  });
});
