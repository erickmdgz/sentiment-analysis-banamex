const SPANISH_MONTHS = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

export function formatNPS(nps: number | null | undefined): string {
  if (nps === null || nps === undefined || Number.isNaN(nps)) return '—';
  const rounded = Math.round(nps * 10) / 10;
  return rounded > 0 ? `+${rounded}` : `${rounded}`;
}

export function formatPct(pct: number | null | undefined, decimals = 1): string {
  if (pct === null || pct === undefined || Number.isNaN(pct)) return '—';
  return `${pct.toFixed(decimals)}%`;
}

export function formatInt(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('es-MX').format(n);
}

export function formatMonthLabel(yyyymm: string): string {
  const [yearStr, monthStr] = yyyymm.split('-');
  const monthIdx = Number(monthStr) - 1;
  if (monthIdx < 0 || monthIdx > 11) return yyyymm;
  return `${SPANISH_MONTHS[monthIdx]} ${yearStr}`;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

export function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}
