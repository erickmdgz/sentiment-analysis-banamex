import { describe, expect, it, beforeAll, afterAll, beforeEach } from 'vitest';
import { server } from '@/mocks/server';
import { TOKEN_KEY } from '@/api/client';
import {
  TOTAL_BRANCHES,
  MONTHS_AVAILABLE,
  makeFakeJWT,
} from '@/mocks/fixtures';

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

beforeEach(() => {
  localStorage.setItem(TOKEN_KEY, makeFakeJWT('demo').token);
});

afterAll(() => server.close());

const auth = () => ({ Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}` });

describe('MSW handlers', () => {
  it('GET /healthz no requiere auth', async () => {
    const r = await fetch('/healthz');
    expect(r.status).toBe(200);
    const body = await r.json();
    expect(body.status).toBe('ok');
  });

  it('GET /validation devuelve un ValidationSummary completo', async () => {
    const r = await fetch('/validation', { headers: auth() });
    expect(r.status).toBe(200);
    const body = await r.json();
    expect(body.branches_detected).toBe(TOTAL_BRANCHES);
    expect(body.months_available).toEqual(MONTHS_AVAILABLE);
    expect(body.columns_detected).toContain('record_id');
  });

  it('GET /national/ytd respeta el shape de NationalYTD', async () => {
    const r = await fetch('/national/ytd', { headers: auth() });
    expect(r.status).toBe(200);
    const body = await r.json();
    expect(body.nps).toBeDefined();
    expect(body.nps.distribution.promoters_pct).toBeGreaterThan(0);
    expect(Array.isArray(body.causes)).toBe(true);
    expect(Array.isArray(body.strengths)).toBe(true);
    expect(body.rankings.worst_nps.items.length).toBeGreaterThan(0);
  });

  it('GET /branches devuelve la lista completa de sucursales', async () => {
    const r = await fetch('/branches', { headers: auth() });
    const body = await r.json();
    expect(body.length).toBe(TOTAL_BRANCHES);
    expect(body[0]).toHaveProperty('branch_id');
    expect(body[0]).toHaveProperty('response_count');
    expect(body[0]).toHaveProperty('has_target');
  });

  it('GET /branches/:id/ytd 404 cuando la sucursal no existe', async () => {
    const r = await fetch('/branches/XYZ/ytd', { headers: auth() });
    expect(r.status).toBe(404);
    const body = await r.json();
    expect(body.code).toBe('branch_not_found');
  });

  it('GET /national/compare 422 con mes inválido', async () => {
    const r = await fetch('/national/compare?month_a=2020-01&month_b=2020-02', { headers: auth() });
    expect(r.status).toBe(422);
    const body = await r.json();
    expect(body.code).toBe('invalid_month');
  });

  it('Sin token, todos los endpoints autenticados devuelven 401', async () => {
    localStorage.removeItem(TOKEN_KEY);
    const r = await fetch('/national/ytd');
    expect(r.status).toBe(401);
  });

  it('Fixtures determinísticas: misma sucursal devuelve mismo NPS', async () => {
    const [a, b] = await Promise.all([
      fetch('/branches/A-0001/ytd', { headers: auth() }).then((r) => r.json()),
      fetch('/branches/A-0001/ytd', { headers: auth() }).then((r) => r.json()),
    ]);
    expect(a.nps.nps_actual).toBe(b.nps.nps_actual);
    expect(a.nps.distribution.detractors_count).toBe(b.nps.distribution.detractors_count);
  });
});
