import * as React from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CausesPanel } from '@/components/CausesPanel';
import { StrengthsPanel } from '@/components/StrengthsPanel';
import { CriticalBranchesTable } from '@/components/CriticalBranchesTable';
import { MonthSelector } from '@/components/MonthSelector';
import { useNationalCompare, useValidation } from '@/api/queries';
import { formatInt, formatMonthLabel, formatNPS, formatPct } from '@/lib/format';

interface DeltaRowProps {
  label: string;
  a: number;
  b: number;
  format?: (n: number) => string;
}

function DeltaRow({ label, a, b, format = (n) => n.toFixed(1) }: DeltaRowProps) {
  const delta = b - a;
  return (
    <TableRow>
      <TableCell className="font-medium">{label}</TableCell>
      <TableCell className="text-right font-mono">{format(a)}</TableCell>
      <TableCell className="text-right font-mono">{format(b)}</TableCell>
      <TableCell className="text-right">
        <Badge variant={delta >= 0 ? 'success' : 'danger'} className="font-mono text-[10px]">
          {delta >= 0 ? <ArrowUp className="mr-1 h-3 w-3" /> : <ArrowDown className="mr-1 h-3 w-3" />}
          {delta >= 0 ? '+' : ''}
          {format(delta)}
        </Badge>
      </TableCell>
    </TableRow>
  );
}

export function NationalComparePage() {
  const { data: validation } = useValidation();
  const months = validation?.months_available ?? [];
  const [monthA, setMonthA] = React.useState<string>('');
  const [monthB, setMonthB] = React.useState<string>('');

  React.useEffect(() => {
    if (months.length >= 2 && (!monthA || !monthB)) {
      setMonthA((prev) => prev || months[months.length - 2]);
      setMonthB((prev) => prev || months[months.length - 1]);
    }
  }, [months, monthA, monthB]);

  const compare = useNationalCompare(monthA || null, monthB || null);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Comparación nacional</h1>
        <p className="text-sm text-muted-foreground">
          Selecciona dos meses para ver el delta de NPS, distribución, causas y fortalezas.
        </p>
      </header>

      <Card>
        <CardContent className="grid gap-4 p-5 md:grid-cols-2">
          <MonthSelector label="Mes A" value={monthA} onChange={setMonthA} months={months} />
          <MonthSelector label="Mes B" value={monthB} onChange={setMonthB} months={months} />
        </CardContent>
      </Card>

      {compare.isLoading && <Skeleton className="h-72" />}
      {compare.error && (
        <Card>
          <CardHeader>
            <CardTitle>No se pudo cargar la comparación</CardTitle>
          </CardHeader>
          <CardContent>{compare.error.message}</CardContent>
        </Card>
      )}

      {compare.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Métricas clave</CardTitle>
              <p className="text-xs text-muted-foreground">
                {formatMonthLabel(compare.data.month_a)} → {formatMonthLabel(compare.data.month_b)}
              </p>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Métrica</TableHead>
                    <TableHead className="text-right">{formatMonthLabel(compare.data.month_a)}</TableHead>
                    <TableHead className="text-right">{formatMonthLabel(compare.data.month_b)}</TableHead>
                    <TableHead className="text-right">Cambio</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <DeltaRow label="NPS" a={compare.data.nps_a} b={compare.data.nps_b} format={formatNPS} />
                  <DeltaRow
                    label="% Promotores"
                    a={compare.data.distribution_a.promoters_pct}
                    b={compare.data.distribution_b.promoters_pct}
                    format={(n) => formatPct(n)}
                  />
                  <DeltaRow
                    label="% Pasivos"
                    a={compare.data.distribution_a.passives_pct}
                    b={compare.data.distribution_b.passives_pct}
                    format={(n) => formatPct(n)}
                  />
                  <DeltaRow
                    label="% Detractores"
                    a={compare.data.distribution_a.detractors_pct}
                    b={compare.data.distribution_b.detractors_pct}
                    format={(n) => formatPct(n)}
                  />
                  <DeltaRow
                    label="Respuestas"
                    a={compare.data.distribution_a.promoters_count +
                      compare.data.distribution_a.passives_count +
                      compare.data.distribution_a.detractors_count}
                    b={compare.data.distribution_b.promoters_count +
                      compare.data.distribution_b.passives_count +
                      compare.data.distribution_b.detractors_count}
                    format={(n) => formatInt(n)}
                  />
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <section className="grid gap-4 lg:grid-cols-2">
            <CausesPanel
              title={`Causas — ${formatMonthLabel(compare.data.month_a)}`}
              items={compare.data.causes_a}
              variant="cause"
            />
            <CausesPanel
              title={`Causas — ${formatMonthLabel(compare.data.month_b)}`}
              items={compare.data.causes_b}
              variant="cause"
              description={`Subieron: ${compare.data.causes_increased.join(', ') || '—'} · Bajaron: ${compare.data.causes_decreased.join(', ') || '—'}`}
            />
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <StrengthsPanel
              title={`Fortalezas — ${formatMonthLabel(compare.data.month_a)}`}
              items={compare.data.strengths_a}
            />
            <StrengthsPanel
              title={`Fortalezas — ${formatMonthLabel(compare.data.month_b)}`}
              items={compare.data.strengths_b}
              description={`Subieron: ${compare.data.strengths_increased.join(', ') || '—'} · Bajaron: ${compare.data.strengths_decreased.join(', ') || '—'}`}
            />
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <CriticalBranchesTable
              branches={compare.data.branches_improved}
              title="Más mejoraron"
              description="Sucursales con mayor mejora absoluta del NPS entre los meses."
            />
            <CriticalBranchesTable
              branches={compare.data.branches_worsened}
              title="Más empeoraron"
              description="Sucursales con mayor caída del NPS entre los meses."
            />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Insight narrativo</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                De {formatMonthLabel(compare.data.month_a)} a {formatMonthLabel(compare.data.month_b)}, el NPS nacional{' '}
                {compare.data.nps_change >= 0 ? 'subió' : 'bajó'}{' '}
                <span className="font-mono">{Math.abs(compare.data.nps_change).toFixed(1)}</span> puntos. La{' '}
                {compare.data.nps_change >= 0 ? 'mejora' : 'caída'} se relaciona principalmente con cambios en
                {' '}
                <span className="font-medium">
                  {(compare.data.causes_increased[0] ?? compare.data.causes_decreased[0]) ?? 'fricciones generales'}
                </span>.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
