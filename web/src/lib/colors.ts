export type GapTone = 'green' | 'amber' | 'red';

export function gapTone(gap: number | null | undefined): GapTone {
  if (gap === null || gap === undefined || Number.isNaN(gap)) return 'amber';
  if (gap >= 0) return 'green';
  if (gap <= -10) return 'red';
  return 'amber';
}

export const TONE_BG: Record<GapTone, string> = {
  green: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  amber: 'bg-amber-100 text-amber-800 border-amber-200',
  red: 'bg-rose-100 text-rose-800 border-rose-200',
};

export const TONE_DOT: Record<GapTone, string> = {
  green: 'bg-banamex-green',
  amber: 'bg-banamex-amber',
  red: 'bg-banamex-red',
};

export const TONE_TEXT: Record<GapTone, string> = {
  green: 'text-banamex-green',
  amber: 'text-banamex-amber',
  red: 'text-banamex-red',
};

export const NPS_GROUP_COLOR: Record<'Promotor' | 'Pasivo' | 'Detractor', string> = {
  Promotor: '#16a34a',
  Pasivo: '#f59e0b',
  Detractor: '#dc2626',
};

export const PRIORITY_TONE: Record<'alta' | 'media' | 'baja', GapTone> = {
  alta: 'red',
  media: 'amber',
  baja: 'green',
};
