import * as React from 'react';
import { Link } from 'react-router-dom';
import { ArrowDown, ArrowLeft, ArrowUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CausesPanel } from '@/components/CausesPanel';
import { StrengthsPanel } from '@/components/StrengthsPanel';
import { MonthSelector } from '@/components/MonthSelector';
import { useBranchCompare, useBranchPersonnel, useValidation } from '@/api/queries';
import { useBranch } from '@/hooks/useBranch';
import { formatInt, formatMonthLabel, formatNPS, formatPct } from '@/lib/format';

function DeltaRow({
  label,
  a,
  b,
  format = (n: number) => n.toFixed(1),
}: {
  label: string;
  a: number;
  b: number;
  format?: (n: number) => string;
}) {
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

export function BranchComparePage() {
  const branchId = useBranch();
  const validation = useValidation();
  const months = validation.data?.months_available ?? [];
  const [monthA, setMonthA] = React.useState<string>('');
  const [monthB, setMonthB] = React.useState<string>('');
  React.useEffect(() => {
    if (months.length >= 2 && (!monthA || !monthB)) {
      setMonthA((prev) => prev || months[months.length - 2]);
      setMonthB((prev) => prev || months[months.length - 1]);
    }
  }, [months, monthA, monthB]);

  const compare = useBranchCompare(branchId, monthA || null, monthB || null);
  const personnel = useBranchPersonnel(branchId);

  if (!branchId) return null;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <Link to={`/branches/${branchId}`} className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Volver a {branchId}
          </Link>
        </div>
        <h1 className="text-2xl font-semibold">Comparación · {branchId}</h1>
      </header>

      <Card>
        <CardContent className="grid gap-4 p-5 md:grid-cols-2">
          <MonthSelector label="Mes A" value={monthA} onChange={setMonthA} months={months} />
          <MonthSelector label="Mes B" value={monthB} onChange={setMonthB} months={months} />
        </CardContent>
      </Card>

      {compare.isLoading && <Skeleton className="h-72" />}
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
            />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Cambios en personal mencionado</CardTitle>
              <p className="text-xs text-muted-foreground">
                Personas mencionadas en uno u otro mes con cambios de polaridad o frecuencia.
              </p>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Polaridad actual</TableHead>
                    <TableHead className="text-right">Menciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(personnel.data ?? []).slice(0, 8).map((p) => (
                    <TableRow key={`${p.name}-${p.example_record_id}`}>
                      <TableCell className="font-medium">{p.name}</TableCell>
                      <TableCell>
                        <Badge variant={p.polarity === 'pos' ? 'success' : 'danger'}>
                          {p.polarity === 'pos' ? 'positiva' : 'negativa'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">{p.count}</TableCell>
                    </TableRow>
                  ))}
                  {(personnel.data ?? []).length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-sm text-muted-foreground">
                        Sin variaciones de personal.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
