// Fixtures determinísticas para MSW. Mismo input → mismo output entre reloads.
// Sembradas con mulberry32 a partir de hashes de string (lib/seed.ts).

import { hashString, mulberry32, pick, randFloat, randInt, rng } from '@/lib/seed';
import type {
  AdminFile,
  AdminRuns,
  AnnotationRunRow,
  BranchListItem,
  BranchYTD,
  CauseBucket,
  ClassifierRunRow,
  CoverageSummary,
  CriticalBranch,
  ImpactByCategory,
  Insight,
  MonthlyComparison,
  MonthlyPoint,
  MonthlyTrend,
  NationalYTD,
  NPSDistribution,
  NPSSummary,
  PassiveAnalysis,
  PersonnelMention,
  Rankings,
  RepresentativeComment,
  SuggestedAction,
  UploadStatus,
  ValidationSummary,
  WordFrequency,
} from '@/api/schema';

// ---------------------------------------------------------------------------
// Constantes determinísticas
// ---------------------------------------------------------------------------

export const TOTAL_BRANCHES = 1291;

export const MONTHS_AVAILABLE: string[] = (() => {
  const months: string[] = [];
  // 2025-01 .. 2026-04 = 16 meses
  for (let year = 2025; year <= 2026; year++) {
    const maxMonth = year === 2026 ? 4 : 12;
    for (let m = 1; m <= maxMonth; m++) {
      months.push(`${year}-${String(m).padStart(2, '0')}`);
    }
  }
  return months;
})();

export const CAUSE_BUCKETS: string[] = [
  'Atención del personal',
  'Tiempos y espera',
  'Sucursal física',
  'Cajeros (ATM)',
  'Canales digitales',
  'Productos y promociones',
  'Operaciones transaccionales',
  'Costos',
  'Aclaraciones, quejas y fraude',
  'Procesos y requisitos',
];

export const STRENGTH_BUCKETS: string[] = [
  'Atención del personal',
  'Tiempos y espera',
  'Sucursal física',
  'Cajeros (ATM)',
  'Canales digitales',
  'Productos y promociones',
  'Operaciones transaccionales',
];

const L2_SAMPLES: Record<string, string[]> = {
  'Atención del personal': ['Trato grosero', 'Falta de empatía', 'Personal no capacitado', 'Indiferencia'],
  'Tiempos y espera': ['Fila prolongada', 'Pocos cajeros operando', 'Tiempo de atención excesivo'],
  'Sucursal física': ['Aire acondicionado', 'Limpieza', 'Espacio insuficiente'],
  'Cajeros (ATM)': ['ATM sin efectivo', 'ATM fuera de servicio', 'Errores transaccionales'],
  'Canales digitales': ['App lenta', 'Token desincronizado', 'Caídas frecuentes'],
  'Productos y promociones': ['Tarjeta tardía', 'Promesa incumplida', 'Comisiones inesperadas'],
  'Operaciones transaccionales': ['Cobros indebidos', 'Transferencias bloqueadas', 'Depósitos no acreditados'],
  Costos: ['Comisiones', 'Anualidad', 'CAT alto'],
  'Aclaraciones, quejas y fraude': ['Aclaración sin avance', 'Devolución pendiente', 'Fraude no resuelto'],
  'Procesos y requisitos': ['Requisitos excesivos', 'Trámite presencial obligado', 'Documentación duplicada'],
};

const PRIORITY_VALUES: Array<'alta' | 'media' | 'baja'> = ['alta', 'media', 'baja'];

const FIRST_NAMES = [
  'Ana', 'Carlos', 'María', 'Jorge', 'Lucía', 'Pedro', 'Sofía', 'Diego',
  'Valeria', 'Ricardo', 'Patricia', 'Andrés', 'Gabriela', 'Fernando',
];

const VERBATIM_TEMPLATES = [
  'La atención de {nombre} fue excelente, resolvió mi caso rápidamente.',
  'Esperé más de 40 minutos para una operación sencilla.',
  'El cajero automático estaba fuera de servicio, tuve que regresar otro día.',
  'La aplicación móvil falla constantemente al transferir.',
  'Me cobraron una comisión que nunca autoricé.',
  'La sucursal está bien ubicada pero hace mucho calor adentro.',
  'Personal poco capacitado para resolver dudas sobre inversión.',
  'Trámite muy rápido, todo bien explicado.',
  'Cobros indebidos en mi estado de cuenta sin justificación.',
  'Buen servicio en general, recomiendo la atención de la sucursal.',
];

// ---------------------------------------------------------------------------
// Generadores derivados (puros + sembrados)
// ---------------------------------------------------------------------------

export function makeBranchId(idx: number): string {
  return `A-${String(idx + 1).padStart(4, '0')}`;
}

export interface BranchFact {
  branch_id: string;
  region: string;
  response_count: number;
  has_target: boolean;
  nps_target: number | null;
  nps_actual: number;
  detractors_pct: number;
  passives_pct: number;
  promoters_pct: number;
}

let _branchFactsCache: BranchFact[] | null = null;

export function getBranchFacts(): BranchFact[] {
  if (_branchFactsCache) return _branchFactsCache;
  const result: BranchFact[] = [];
  for (let i = 0; i < TOTAL_BRANCHES; i++) {
    const branch_id = makeBranchId(i);
    const rand = rng(`branch:${branch_id}`);
    const has_target = rand() > 0.06; // ~94% con target
    const nps_target = has_target ? randInt(rand, 55, 78) : null;
    const nps_actual = Math.round(randFloat(rand, 5, 80) * 10) / 10;
    const detractors_pct = Math.round(randFloat(rand, 6, 35) * 10) / 10;
    const promoters_pct = Math.round(
      Math.min(80, Math.max(20, nps_actual + 30 + randFloat(rand, -5, 5))) * 10,
    ) / 10;
    const passives_pct = Math.round(Math.max(0, 100 - detractors_pct - promoters_pct) * 10) / 10;
    const response_count = randInt(rand, 8, 480);
    result.push({
      branch_id,
      region: pick(rand, ['Centro', 'Norte', 'Sur', 'Bajío', 'Occidente', 'Sureste']),
      response_count,
      has_target,
      nps_target,
      nps_actual,
      detractors_pct,
      passives_pct,
      promoters_pct,
    });
  }
  _branchFactsCache = result;
  return result;
}

function buildDistribution(
  promoters_pct: number,
  passives_pct: number,
  detractors_pct: number,
  total: number,
): NPSDistribution {
  return {
    promoters_pct,
    passives_pct,
    detractors_pct,
    promoters_count: Math.round((promoters_pct / 100) * total),
    passives_count: Math.round((passives_pct / 100) * total),
    detractors_count: Math.round((detractors_pct / 100) * total),
  };
}

function npsFromFact(fact: BranchFact): NPSSummary {
  const gap = fact.nps_target !== null ? Math.round((fact.nps_actual - fact.nps_target) * 10) / 10 : null;
  return {
    nps_actual: fact.nps_actual,
    nps_target: fact.nps_target,
    gap,
    total_responses: fact.response_count,
    distribution: buildDistribution(
      fact.promoters_pct,
      fact.passives_pct,
      fact.detractors_pct,
      fact.response_count,
    ),
  };
}

function trendFromFact(seed: string, baseline: number, totalResponses: number): MonthlyTrend {
  const rand = rng(`trend:${seed}`);
  const points: MonthlyPoint[] = MONTHS_AVAILABLE.map((month, idx) => {
    const wobble = randFloat(rand, -8, 8);
    const progression = (idx - MONTHS_AVAILABLE.length / 2) * 0.6;
    const nps = Math.max(-20, Math.min(95, Math.round((baseline + wobble + progression) * 10) / 10));
    const responses = Math.max(5, Math.round((totalResponses / MONTHS_AVAILABLE.length) * randFloat(rand, 0.6, 1.4)));
    return { month, nps, responses };
  });
  return { points };
}

export function makeCauseBuckets(seed: string, buckets: string[], totalResponses: number): CauseBucket[] {
  const rand = rng(seed);
  return buckets
    .map((bucket) => {
      const r = rng(`${seed}:${bucket}`);
      const count = randInt(r, 12, Math.max(20, Math.floor(totalResponses * 0.4)));
      const pct_of_group = Math.round(randFloat(r, 5, 35) * 10) / 10;
      const sample_pool = L2_SAMPLES[bucket] ?? [bucket];
      return {
        bucket,
        count,
        pct_of_group,
        sample_l2: sample_pool.slice(0, 3),
      } satisfies CauseBucket;
    })
    .sort((a, b) => b.count - a.count)
    .map((entry, idx) => ({
      ...entry,
      // pequeño "ruido" determinístico para que el ranking cambie entre series A/B
      count: entry.count + (rand() > 0.5 ? idx : -idx),
    }))
    .sort((a, b) => b.count - a.count);
}

export function makeCriticalBranches(seed: string, n = 10): CriticalBranch[] {
  const branches = getBranchFacts();
  const sorted = [...branches]
    .filter((b) => b.has_target)
    .sort((a, b) => {
      const gA = (a.nps_target ?? 60) - a.nps_actual;
      const gB = (b.nps_target ?? 60) - b.nps_actual;
      return gB - gA;
    })
    .slice(0, n);
  const conditions = [
    'NPS por debajo de objetivo',
    'Brecha > 10 puntos',
    'Detractores > 25%',
    'Tendencia descendente 3 meses',
  ];
  return sorted.map((b) => {
    const rand = rng(`${seed}:critical:${b.branch_id}`);
    const triggered: string[] = [];
    if (b.nps_target !== null && b.nps_actual < b.nps_target) triggered.push(conditions[0]);
    if (b.nps_target !== null && b.nps_target - b.nps_actual > 10) triggered.push(conditions[1]);
    if (b.detractors_pct > 25) triggered.push(conditions[2]);
    if (rand() > 0.5) triggered.push(conditions[3]);
    return {
      branch_id: b.branch_id,
      nps_actual: b.nps_actual,
      nps_target: b.nps_target,
      gap: b.nps_target !== null ? Math.round((b.nps_actual - b.nps_target) * 10) / 10 : null,
      detractors_pct: b.detractors_pct,
      triggered_conditions: triggered.length > 0 ? triggered : [conditions[0]],
    } satisfies CriticalBranch;
  });
}

function makeRankings(): Rankings {
  const branches = getBranchFacts();
  const sortedByNps = [...branches].sort((a, b) => a.nps_actual - b.nps_actual);
  const withGap = branches.filter((b) => b.nps_target !== null);
  const sortedByGap = [...withGap].sort(
    (a, b) => (a.nps_actual - (a.nps_target ?? 0)) - (b.nps_actual - (b.nps_target ?? 0)),
  );
  const sortedByDetractors = [...branches].sort((a, b) => b.detractors_pct - a.detractors_pct);

  return {
    worst_nps: {
      name: 'Peor NPS',
      items: sortedByNps.slice(0, 5).map((b) => ({
        branch_id: b.branch_id,
        value: b.nps_actual,
        label: `NPS ${b.nps_actual.toFixed(1)}`,
      })),
    },
    worst_gap: {
      name: 'Mayor brecha vs objetivo',
      items: sortedByGap.slice(0, 5).map((b) => ({
        branch_id: b.branch_id,
        value: b.nps_actual - (b.nps_target ?? 0),
        label: `Brecha ${(b.nps_actual - (b.nps_target ?? 0)).toFixed(1)}`,
      })),
    },
    most_detractors: {
      name: '% Detractores más alto',
      items: sortedByDetractors.slice(0, 5).map((b) => ({
        branch_id: b.branch_id,
        value: b.detractors_pct,
        label: `${b.detractors_pct.toFixed(1)}% detractores`,
      })),
    },
    worsened: {
      name: 'Empeoraron mes a mes',
      items: sortedByNps.slice(0, 5).map((b) => ({
        branch_id: b.branch_id,
        value: -Math.abs(Math.round(b.detractors_pct - 15)),
        label: 'Tendencia negativa',
      })),
    },
    improved: {
      name: 'Mejoraron mes a mes',
      items: [...branches]
        .sort((a, b) => b.nps_actual - a.nps_actual)
        .slice(0, 5)
        .map((b) => ({
          branch_id: b.branch_id,
          value: Math.round(b.nps_actual - 50),
          label: 'Tendencia positiva',
        })),
    },
  };
}

export function makeActions(seed: string, n: number): SuggestedAction[] {
  const rand = rng(`actions:${seed}`);
  return Array.from({ length: n }, (_, i) => {
    const bucket = pick(rand, CAUSE_BUCKETS);
    const priority = PRIORITY_VALUES[i % PRIORITY_VALUES.length];
    return {
      text: `Reforzar protocolo de ${bucket.toLowerCase()} con capacitación dirigida y seguimiento semanal.`,
      priority,
      related_bucket: bucket,
      related_branches: getBranchFacts()
        .slice(i * 3, i * 3 + 3)
        .map((b) => b.branch_id),
    };
  });
}

function makeImpact(): ImpactByCategory[] {
  const rand = rng('impact');
  return CAUSE_BUCKETS.map((bucket) => ({
    bucket,
    impact_points: Math.round(randFloat(rand, 1, 9) * 10) / 10,
  })).sort((a, b) => b.impact_points - a.impact_points);
}

export function makeInsights(seed: string, n: number): Insight[] {
  const categories: Insight['category'][] = [
    'nps',
    'brecha',
    'fortaleza',
    'fricción',
    'personal',
    'comparación',
    'cobertura',
  ];
  // RNG sembrado para que el ordenamiento futuro sea determinístico aunque
  // ahora solo iteremos el template.
  rng(`insights:${seed}`);
  return Array.from({ length: n }, (_, idx) => ({
    text: TEMPLATE_INSIGHTS[idx % TEMPLATE_INSIGHTS.length],
    category: categories[idx % categories.length],
  }));
}

const TEMPLATE_INSIGHTS = [
  'El NPS nacional cerró 18.4 puntos por debajo del objetivo anual.',
  'Atención del personal explica el 32% de los detractores activos.',
  'Sucursal A-0042 representa el 4.1% de los detractores nacionales.',
  'Tiempos y espera se mantienen como la fricción más mencionada por pasivos.',
  'Cajeros (ATM) bajaron 6 puntos en menciones entre marzo y abril.',
  'Comentarios sobre personal positivo crecieron 12% mes a mes.',
  'Costos y comisiones afectan principalmente al segmento promotores en riesgo de bajar.',
  '18% de sucursales no tienen NPS objetivo configurado en la fuente interna.',
];

// ---------------------------------------------------------------------------
// API pública
// ---------------------------------------------------------------------------

export function getValidationSummary(): ValidationSummary {
  const branches = getBranchFacts();
  const totalRows = branches.reduce((acc, b) => acc + b.response_count, 0);
  return {
    files_processed: 3,
    rows_loaded: totalRows,
    rows_new: Math.floor(totalRows * 0.94),
    rows_duplicated_ignored: Math.floor(totalRows * 0.06),
    branches_detected: TOTAL_BRANCHES,
    period_available: [`${MONTHS_AVAILABLE[0]}-01`, `${MONTHS_AVAILABLE[MONTHS_AVAILABLE.length - 1]}-28`],
    months_available: [...MONTHS_AVAILABLE],
    columns_detected: [
      'record_id',
      'response_date',
      'nps_group',
      'nps_rate',
      'verbatim',
      'branch_id',
    ],
    rows_valid: Math.floor(totalRows * 0.95),
    rows_empty_verbatim: Math.floor(totalRows * 0.18),
    rows_invalid_nps: Math.floor(totalRows * 0.002),
    rows_missing_branch: Math.floor(totalRows * 0.001),
    rows_duplicate_record_id: Math.floor(totalRows * 0.005),
    rows_invalid_date: Math.floor(totalRows * 0.001),
  };
}

export function getCoverageSummary(): CoverageSummary {
  const branches = getBranchFacts();
  const withTarget = branches.filter((b) => b.has_target);
  const withoutTarget = branches.filter((b) => !b.has_target).map((b) => b.branch_id);
  const noResponses = withTarget
    .filter((b) => b.response_count < 12)
    .slice(0, 18)
    .map((b) => b.branch_id);
  return {
    branches_detected: TOTAL_BRANCHES,
    branches_with_target: withTarget.length,
    branches_without_target: withoutTarget,
    branches_with_target_no_responses: noResponses,
    invalid_targets: [],
    duplicate_targets: [],
  };
}

export function getNationalSummary(): NPSSummary {
  const branches = getBranchFacts();
  const total = branches.reduce((acc, b) => acc + b.response_count, 0);
  const weightedNps =
    branches.reduce((acc, b) => acc + b.nps_actual * b.response_count, 0) / total;
  const weightedTarget =
    branches
      .filter((b) => b.nps_target !== null)
      .reduce((acc, b) => acc + (b.nps_target ?? 0) * b.response_count, 0) /
    branches
      .filter((b) => b.nps_target !== null)
      .reduce((acc, b) => acc + b.response_count, 0);
  const promoters_pct = Math.round(
    (branches.reduce((acc, b) => acc + (b.promoters_pct / 100) * b.response_count, 0) / total) * 1000,
  ) / 10;
  const passives_pct = Math.round(
    (branches.reduce((acc, b) => acc + (b.passives_pct / 100) * b.response_count, 0) / total) * 1000,
  ) / 10;
  const detractors_pct = Math.round(
    (branches.reduce((acc, b) => acc + (b.detractors_pct / 100) * b.response_count, 0) / total) * 1000,
  ) / 10;

  const nps_actual = Math.round(weightedNps * 10) / 10;
  const nps_target = Math.round(weightedTarget * 10) / 10;
  return {
    nps_actual,
    nps_target,
    gap: Math.round((nps_actual - nps_target) * 10) / 10,
    total_responses: total,
    distribution: buildDistribution(promoters_pct, passives_pct, detractors_pct, total),
  };
}

export function getNationalYTD(): NationalYTD {
  const nps = getNationalSummary();
  return {
    nps,
    trend: trendFromFact('national', nps.nps_actual, nps.total_responses),
    causes: makeCauseBuckets('national:causes', CAUSE_BUCKETS, nps.total_responses).slice(0, 10),
    strengths: makeCauseBuckets('national:strengths', STRENGTH_BUCKETS, nps.total_responses).slice(0, 10),
    critical_branches: makeCriticalBranches('national', 10),
    rankings: makeRankings(),
    actions: makeActions('national', 10),
    impact: makeImpact(),
    insights: makeInsights('national', 8),
    branches_total: TOTAL_BRANCHES,
    branches_with_target: getBranchFacts().filter((b) => b.has_target).length,
  };
}

export function getNationalTrend(): MonthlyTrend {
  const nps = getNationalSummary();
  return trendFromFact('national', nps.nps_actual, nps.total_responses);
}

export function getNationalPassiveAnalysis(): PassiveAnalysis {
  const total = getNationalSummary().total_responses;
  return {
    near_detractor: makeCauseBuckets('passive:detractor', CAUSE_BUCKETS, total).slice(0, 6),
    near_promoter: makeCauseBuckets('passive:promoter', STRENGTH_BUCKETS, total).slice(0, 6),
  };
}

function getMonthDistribution(seed: string, npsBase: number, responses: number): NPSDistribution {
  const r = rng(`dist:${seed}`);
  const promoters_pct = Math.round(Math.max(20, Math.min(75, npsBase + 25 + randFloat(r, -8, 8))) * 10) / 10;
  const detractors_pct = Math.round(Math.max(5, Math.min(35, 28 - npsBase * 0.2 + randFloat(r, -4, 4))) * 10) / 10;
  const passives_pct = Math.round(Math.max(0, 100 - promoters_pct - detractors_pct) * 10) / 10;
  return buildDistribution(promoters_pct, passives_pct, detractors_pct, responses);
}

export function getNationalCompare(monthA: string, monthB: string): MonthlyComparison {
  const branches = getBranchFacts();
  const totalA = Math.round(
    branches.reduce((acc, b) => acc + b.response_count, 0) / MONTHS_AVAILABLE.length,
  );
  const totalB = totalA + Math.round(totalA * (randFloat(rng(`vol:${monthB}`), -0.12, 0.12)));
  const npsA = Math.round(randFloat(rng(`a:${monthA}`), 35, 55) * 10) / 10;
  const npsB = Math.round((npsA + randFloat(rng(`delta:${monthA}:${monthB}`), -7, 7)) * 10) / 10;
  const distA = getMonthDistribution(`A:${monthA}`, npsA, totalA);
  const distB = getMonthDistribution(`B:${monthB}`, npsB, totalB);
  const causesA = makeCauseBuckets(`causesA:${monthA}`, CAUSE_BUCKETS, totalA).slice(0, 8);
  const causesB = makeCauseBuckets(`causesB:${monthB}`, CAUSE_BUCKETS, totalB).slice(0, 8);
  const strengthsA = makeCauseBuckets(`strA:${monthA}`, STRENGTH_BUCKETS, totalA).slice(0, 6);
  const strengthsB = makeCauseBuckets(`strB:${monthB}`, STRENGTH_BUCKETS, totalB).slice(0, 6);
  return {
    month_a: monthA,
    month_b: monthB,
    nps_a: npsA,
    nps_b: npsB,
    nps_change: Math.round((npsB - npsA) * 10) / 10,
    distribution_a: distA,
    distribution_b: distB,
    causes_a: causesA,
    causes_b: causesB,
    causes_increased: causesB.slice(0, 2).map((c) => c.bucket),
    causes_decreased: causesA.slice(-2).map((c) => c.bucket),
    strengths_a: strengthsA,
    strengths_b: strengthsB,
    strengths_increased: strengthsB.slice(0, 2).map((c) => c.bucket),
    strengths_decreased: strengthsA.slice(-2).map((c) => c.bucket),
    branches_improved: makeCriticalBranches(`improved:${monthB}`, 5),
    branches_worsened: makeCriticalBranches(`worsened:${monthA}`, 5),
    actions: makeActions(`compare:${monthA}:${monthB}`, 5),
  };
}

// --- Sucursales ---

export function findBranch(branchId: string): BranchFact | null {
  return getBranchFacts().find((b) => b.branch_id === branchId) ?? null;
}

export function listBranches(query?: string): BranchListItem[] {
  const branches = getBranchFacts();
  const q = (query ?? '').trim().toLowerCase();
  const filtered = q
    ? branches.filter((b) => b.branch_id.toLowerCase().includes(q))
    : branches;
  return filtered.map((b) => ({
    branch_id: b.branch_id,
    response_count: b.response_count,
    has_target: b.has_target,
  }));
}

export function getBranchYTD(branchId: string): BranchYTD | null {
  const fact = findBranch(branchId);
  if (!fact) return null;
  const nps = npsFromFact(fact);
  return {
    branch_id: branchId,
    nps,
    trend: trendFromFact(branchId, nps.nps_actual, nps.total_responses),
    causes: makeCauseBuckets(`branch:${branchId}:causes`, CAUSE_BUCKETS, nps.total_responses).slice(0, 8),
    strengths: makeCauseBuckets(`branch:${branchId}:strengths`, STRENGTH_BUCKETS, nps.total_responses).slice(0, 8),
    actions: makeActions(`branch:${branchId}`, 6),
    insights: makeInsights(`branch:${branchId}`, 5),
    top_words: getBranchWords(branchId, null, 30),
    representatives: getBranchRepresentatives(branchId, 2),
    personnel: getBranchPersonnel(branchId),
  };
}

export function getBranchTrend(branchId: string): MonthlyTrend {
  const fact = findBranch(branchId);
  if (!fact) return { points: [] };
  return trendFromFact(branchId, fact.nps_actual, fact.response_count);
}

export function getBranchCompare(branchId: string, monthA: string, monthB: string): MonthlyComparison {
  const fact = findBranch(branchId) ?? getBranchFacts()[0];
  const rand = rng(`branch:${branchId}:cmp:${monthA}:${monthB}`);
  const npsA = Math.round((fact.nps_actual + randFloat(rand, -7, 7)) * 10) / 10;
  const npsB = Math.round((npsA + randFloat(rand, -6, 6)) * 10) / 10;
  const totalA = Math.max(8, Math.round(fact.response_count / MONTHS_AVAILABLE.length));
  const totalB = totalA + randInt(rand, -4, 6);
  const distA = getMonthDistribution(`branchA:${branchId}:${monthA}`, npsA, totalA);
  const distB = getMonthDistribution(`branchB:${branchId}:${monthB}`, npsB, totalB);
  const causesA = makeCauseBuckets(`branch:${branchId}:causesA:${monthA}`, CAUSE_BUCKETS, totalA).slice(0, 6);
  const causesB = makeCauseBuckets(`branch:${branchId}:causesB:${monthB}`, CAUSE_BUCKETS, totalB).slice(0, 6);
  return {
    month_a: monthA,
    month_b: monthB,
    nps_a: npsA,
    nps_b: npsB,
    nps_change: Math.round((npsB - npsA) * 10) / 10,
    distribution_a: distA,
    distribution_b: distB,
    causes_a: causesA,
    causes_b: causesB,
    causes_increased: causesB.slice(0, 2).map((c) => c.bucket),
    causes_decreased: causesA.slice(-2).map((c) => c.bucket),
    strengths_a: makeCauseBuckets(`branch:${branchId}:strA:${monthA}`, STRENGTH_BUCKETS, totalA).slice(0, 4),
    strengths_b: makeCauseBuckets(`branch:${branchId}:strB:${monthB}`, STRENGTH_BUCKETS, totalB).slice(0, 4),
    strengths_increased: [],
    strengths_decreased: [],
    branches_improved: [],
    branches_worsened: [],
    actions: makeActions(`branch:${branchId}:cmp:${monthA}:${monthB}`, 3),
  };
}

const WORDS_BY_GROUP: Record<string, string[]> = {
  Detractor: [
    'espera', 'lento', 'cobro', 'comisión', 'fila', 'tarde', 'molestia', 'fraude',
    'aclaración', 'pésimo', 'amabilidad', 'cajero', 'fallo', 'app', 'rechazo',
    'rudo', 'documentación', 'requisitos', 'transferencia', 'horario',
  ],
  Promotor: [
    'rápido', 'amable', 'excelente', 'eficiente', 'claro', 'profesional', 'atento',
    'recomiendo', 'cordial', 'limpio', 'ágil', 'organizado', 'capacitado', 'preciso',
    'puntual', 'útil', 'confianza', 'cercano', 'positivo', 'sólido',
  ],
  General: [
    'sucursal', 'atención', 'servicio', 'persona', 'cliente', 'cajero', 'oficina',
    'cuenta', 'banco', 'banamex', 'asesor', 'gerente', 'turno', 'pago', 'app',
    'tarjeta', 'efectivo', 'depósito', 'transferencia', 'comisión',
  ],
};

export function getBranchWords(branchId: string, group: string | null, topN: number): WordFrequency[] {
  const key = group && WORDS_BY_GROUP[group] ? group : 'General';
  const pool = WORDS_BY_GROUP[key];
  const rand = rng(`words:${branchId}:${key}`);
  return pool
    .slice(0, topN)
    .map((word) => ({
      word,
      count: randInt(rand, 4, 80),
      group: group ? (group as 'Promotor' | 'Detractor' | 'Pasivo') : null,
    }))
    .sort((a, b) => b.count - a.count);
}

export function getBranchRepresentatives(branchId: string, nPerTopic: number): RepresentativeComment[] {
  const rand = rng(`reps:${branchId}`);
  const buckets = CAUSE_BUCKETS.slice(0, 4);
  const result: RepresentativeComment[] = [];
  for (const bucket of buckets) {
    for (let i = 0; i < nPerTopic; i++) {
      const r = rng(`reps:${branchId}:${bucket}:${i}`);
      const verbatim = VERBATIM_TEMPLATES[Math.floor(r() * VERBATIM_TEMPLATES.length)].replace(
        '{nombre}',
        pick(r, FIRST_NAMES),
      );
      const nps_rate = randInt(r, 0, 10);
      const nps_group: 'Promotor' | 'Pasivo' | 'Detractor' =
        nps_rate >= 9 ? 'Promotor' : nps_rate >= 7 ? 'Pasivo' : 'Detractor';
      result.push({
        record_id: `${branchId}-${bucket.slice(0, 3).toUpperCase()}-${i}`,
        verbatim,
        nps_rate,
        nps_group,
        response_date: `2026-${String(randInt(rand, 1, 4)).padStart(2, '0')}-${String(randInt(rand, 1, 28)).padStart(2, '0')}`,
        bucket,
      });
    }
  }
  return result;
}

export function getBranchPersonnel(branchId: string): PersonnelMention[] {
  const rand = rng(`personnel:${branchId}`);
  const names: PersonnelMention[] = [];
  const total = randInt(rand, 3, 7);
  for (let i = 0; i < total; i++) {
    const r = rng(`personnel:${branchId}:${i}`);
    const name = pick(r, FIRST_NAMES);
    const polarity: 'pos' | 'neg' = r() > 0.4 ? 'pos' : 'neg';
    names.push({
      name,
      polarity,
      count: randInt(r, 1, 12),
      example_record_id: `${branchId}-PER-${i}`,
      example_verbatim: VERBATIM_TEMPLATES[0].replace('{nombre}', name),
    });
  }
  return names.sort((a, b) => b.count - a.count);
}

// --- Admin ---

export function getAdminFiles(): AdminFile[] {
  return [
    {
      id: 1,
      filename: '1_mitad_2025c.txt',
      sha256: 'a1b2c3d4'.repeat(8),
      rows_inserted: 132_018,
      uploaded_at: '2026-04-12T10:14:00Z',
    },
    {
      id: 2,
      filename: '2_mitad_2025.txt',
      sha256: 'b2c3d4e5'.repeat(8),
      rows_inserted: 121_447,
      uploaded_at: '2026-04-12T10:17:00Z',
    },
    {
      id: 3,
      filename: '1_mitad_2026.txt',
      sha256: 'c3d4e5f6'.repeat(8),
      rows_inserted: 72_318,
      uploaded_at: '2026-04-15T09:02:00Z',
    },
  ];
}

export function getAdminRuns(): AdminRuns {
  const annotation_runs: AnnotationRunRow[] = [
    {
      id: 1,
      sample_size: 2000,
      model: 'qwen2.5:7b-instruct',
      started_at: '2026-04-10T12:00:00Z',
      finished_at: '2026-04-10T13:18:00Z',
      runtime_seconds: 4680,
      status: 'done',
    },
  ];
  const classifier_runs: ClassifierRunRow[] = [
    {
      id: 1,
      model_path: 'data/models/classifier.joblib',
      trained_on_run_id: 1,
      trained_at: '2026-04-10T13:25:00Z',
      n_samples: 1800,
      n_labels: 15,
      f1_micro: 0.78,
      f1_macro: 0.66,
      hamming_loss: 0.04,
    },
  ];
  return { annotation_runs, classifier_runs };
}

// --- Upload ---

interface UploadJob {
  status: UploadStatus['status'];
  progress: number;
  startedAt: number;
}

const UPLOAD_JOBS = new Map<number, UploadJob>();
let nextUploadId = 100;

export function registerUploadJob(): number {
  const id = nextUploadId++;
  UPLOAD_JOBS.set(id, { status: 'parsing', progress: 0, startedAt: Date.now() });
  return id;
}

export function pollUploadStatus(id: number): UploadStatus {
  const job = UPLOAD_JOBS.get(id) ?? { status: 'done', progress: 1, startedAt: Date.now() };
  const elapsed = Date.now() - job.startedAt;
  // Simula avance: ~3 segundos parsing, ~3 segundos classifying, luego done.
  if (elapsed < 1500) {
    job.status = 'parsing';
    job.progress = Math.min(0.45, elapsed / 1500 * 0.45);
  } else if (elapsed < 3500) {
    job.status = 'classifying';
    job.progress = Math.min(0.95, 0.45 + ((elapsed - 1500) / 2000) * 0.5);
  } else {
    job.status = 'done';
    job.progress = 1;
  }
  UPLOAD_JOBS.set(id, job);
  return {
    file_id: id,
    status: job.status,
    progress: Math.round(job.progress * 100) / 100,
    error: null,
  };
}

// --- Token JWT fake ---

export function makeFakeJWT(username: string): { token: string; expires_at: string } {
  const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' })).replace(/=+$/, '');
  const exp = Math.floor(Date.now() / 1000) + 8 * 60 * 60;
  const payload = btoa(JSON.stringify({ sub: username, exp })).replace(/=+$/, '');
  return {
    token: `${header}.${payload}.demo`,
    expires_at: new Date(exp * 1000).toISOString(),
  };
}

// Re-export útil para tests
export const __internals = { hashString, mulberry32 };
