import { http, HttpResponse, delay } from 'msw';
import {
  findBranch,
  getAdminFiles,
  getAdminRuns,
  getBranchCompare,
  getBranchPersonnel,
  getBranchRepresentatives,
  getBranchTrend,
  getBranchWords,
  getBranchYTD,
  getCoverageSummary,
  getNationalCompare,
  getNationalPassiveAnalysis,
  getNationalTrend,
  getNationalYTD,
  getValidationSummary,
  listBranches,
  makeFakeJWT,
  pollUploadStatus,
  registerUploadJob,
  MONTHS_AVAILABLE,
  CAUSE_BUCKETS,
  STRENGTH_BUCKETS,
  makeCriticalBranches,
  makeActions,
  makeInsights,
  makeCauseBuckets,
} from './fixtures';
import type { ErrorResponse } from '@/api/schema';

type AnyResponse = ReturnType<typeof HttpResponse.json>;

function jsonError(status: number, body: ErrorResponse): AnyResponse {
  return HttpResponse.json(body, { status });
}

function ensureAuth(request: Request): AnyResponse | null {
  const header = request.headers.get('Authorization');
  if (!header?.startsWith('Bearer ')) {
    return jsonError(401, {
      detail: 'Sesión inválida o expirada',
      code: 'unauthorized',
      hint: 'Inicia sesión nuevamente.',
    });
  }
  return null;
}

function ensureMonth(monthA: string | null, monthB: string | null): AnyResponse | null {
  for (const month of [monthA, monthB]) {
    if (!month || !MONTHS_AVAILABLE.includes(month)) {
      return jsonError(422, {
        detail: 'Mes inválido o no disponible',
        code: 'invalid_month',
        hint: `Meses válidos: ${MONTHS_AVAILABLE.join(', ')}`,
      });
    }
  }
  return null;
}

export const handlers = [
  // --- Health ---
  http.get('/healthz', () =>
    HttpResponse.json({
      status: 'ok',
      db_path: 'data/processed/banamex.db',
      classifier_loaded: true,
    }),
  ),

  // --- Auth ---
  http.post('/auth/login', async ({ request }) => {
    const body = (await request.json().catch(() => null)) as { username?: string; password?: string } | null;
    const username = body?.username?.trim() ?? '';
    if (!username) {
      return jsonError(422, { detail: 'Falta el usuario', code: 'missing_username' });
    }
    await delay(120);
    return HttpResponse.json(makeFakeJWT(username));
  }),

  http.get('/auth/me', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const header = request.headers.get('Authorization')!;
    const token = header.slice('Bearer '.length);
    let username = 'demo';
    try {
      const [, payload] = token.split('.');
      const decoded = JSON.parse(atob(payload));
      username = decoded.sub ?? 'demo';
    } catch {
      // fallback al default
    }
    return HttpResponse.json({ username });
  }),

  // --- Upload + validación ---
  http.post('/upload', async ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const id = registerUploadJob();
    await delay(180);
    return HttpResponse.json({
      file_id: id,
      validation_summary: getValidationSummary(),
      already_processed: false,
    });
  }),

  http.get('/upload/:fileId/status', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const id = Number(params.fileId);
    return HttpResponse.json(pollUploadStatus(id));
  }),

  http.get('/validation', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getValidationSummary());
  }),

  http.get('/validation/coverage', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getCoverageSummary());
  }),

  // --- Nacional ---
  http.get('/national/ytd', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getNationalYTD());
  }),

  http.get('/national/trend', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getNationalTrend());
  }),

  http.get('/national/compare', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const monthA = url.searchParams.get('month_a');
    const monthB = url.searchParams.get('month_b');
    const monthErr = ensureMonth(monthA, monthB);
    if (monthErr) return monthErr;
    return HttpResponse.json(getNationalCompare(monthA as string, monthB as string));
  }),

  http.get('/national/critical-branches', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? '10');
    return HttpResponse.json(makeCriticalBranches('national', limit));
  }),

  http.get('/national/rankings', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getNationalYTD().rankings);
  }),

  http.get('/national/causes', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? '10');
    return HttpResponse.json(makeCauseBuckets('national:causes', CAUSE_BUCKETS, 5000).slice(0, limit));
  }),

  http.get('/national/strengths', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? '10');
    return HttpResponse.json(makeCauseBuckets('national:strengths', STRENGTH_BUCKETS, 5000).slice(0, limit));
  }),

  http.get('/national/actions', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? '10');
    return HttpResponse.json(makeActions('national', limit));
  }),

  http.get('/national/impact', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getNationalYTD().impact);
  }),

  http.get('/national/insights', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(makeInsights('national', 8));
  }),

  http.get('/national/passive-analysis', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getNationalPassiveAnalysis());
  }),

  // --- Sucursales ---
  http.get('/branches', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const query = url.searchParams.get('q') ?? '';
    return HttpResponse.json(listBranches(query));
  }),

  http.get('/branches/:id/ytd', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const data = getBranchYTD(String(params.id));
    if (!data) {
      return jsonError(404, {
        detail: 'Sucursal no encontrada',
        code: 'branch_not_found',
      });
    }
    return HttpResponse.json(data);
  }),

  http.get('/branches/:id/trend', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getBranchTrend(String(params.id)));
  }),

  http.get('/branches/:id/compare', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const monthA = url.searchParams.get('month_a');
    const monthB = url.searchParams.get('month_b');
    const monthErr = ensureMonth(monthA, monthB);
    if (monthErr) return monthErr;
    return HttpResponse.json(getBranchCompare(String(params.id), monthA as string, monthB as string));
  }),

  http.get('/branches/:id/causes', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const branchId = String(params.id);
    if (!findBranch(branchId)) {
      return jsonError(404, { detail: 'Sucursal no encontrada', code: 'branch_not_found' });
    }
    return HttpResponse.json(getBranchYTD(branchId)?.causes ?? []);
  }),

  http.get('/branches/:id/strengths', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const branchId = String(params.id);
    if (!findBranch(branchId)) {
      return jsonError(404, { detail: 'Sucursal no encontrada', code: 'branch_not_found' });
    }
    return HttpResponse.json(getBranchYTD(branchId)?.strengths ?? []);
  }),

  http.get('/branches/:id/words', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const group = url.searchParams.get('group');
    const topN = Number(url.searchParams.get('top_n') ?? '30');
    return HttpResponse.json(getBranchWords(String(params.id), group, topN));
  }),

  http.get('/branches/:id/representatives', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    const url = new URL(request.url);
    const nPerTopic = Number(url.searchParams.get('n_per_topic') ?? '2');
    return HttpResponse.json(getBranchRepresentatives(String(params.id), nPerTopic));
  }),

  http.get('/branches/:id/personnel', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getBranchPersonnel(String(params.id)));
  }),

  http.get('/branches/:id/actions', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(makeActions(`branch:${String(params.id)}`, 6));
  }),

  http.get('/branches/:id/insights', ({ params, request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(makeInsights(`branch:${String(params.id)}`, 5));
  }),

  // --- Admin ---
  http.get('/admin/files', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getAdminFiles());
  }),

  http.get('/admin/runs', ({ request }) => {
    const err = ensureAuth(request);
    if (err) return err;
    return HttpResponse.json(getAdminRuns());
  }),
];
