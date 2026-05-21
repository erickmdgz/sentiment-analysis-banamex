import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { NPSCard } from '@/components/NPSCard';
import { DistributionChart } from '@/components/DistributionChart';
import { TrendChart } from '@/components/TrendChart';
import { CausesPanel } from '@/components/CausesPanel';
import { StrengthsPanel } from '@/components/StrengthsPanel';
import { CriticalBranchesTable } from '@/components/CriticalBranchesTable';
import { RankingsPanel } from '@/components/RankingsPanel';
import { ActionsPanel } from '@/components/ActionsPanel';
import { InsightsList } from '@/components/InsightsList';
import { SyntheticTargetsBanner } from '@/components/SyntheticTargetsBanner';
import { useNationalPassiveAnalysis, useNationalYTD } from '@/api/queries';
import { formatInt } from '@/lib/format';

function ImpactSection({ items }: { items: Array<{ bucket: string; impact_points: number }> }) {
  const sorted = [...items].sort((a, b) => b.impact_points - a.impact_points);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Impacto estimado por categoría</CardTitle>
        <p className="text-xs text-muted-foreground">
          Puntos de NPS que ganaría la operación al eliminar la fricción asociada.
        </p>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {sorted.map((item) => (
          <div key={item.bucket} className="flex items-center justify-between rounded-md border border-border p-2">
            <span>Esta categoría representa <span className="font-mono">{item.impact_points.toFixed(1)}</span> puntos perdidos de NPS</span>
            <Badge variant="outline">{item.bucket}</Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function PassiveSection() {
  const { data, isLoading } = useNationalPassiveAnalysis();
  if (isLoading || !data) {
    return <Skeleton className="h-48" />;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Voz de los pasivos</CardTitle>
        <p className="text-xs text-muted-foreground">
          Qué dicen los pasivos cerca de detractor (NPS=7) y cerca de promotor (NPS=8).
        </p>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <CausesPanel
          title="Pasivos cerca de detractor (NPS=7)"
          items={data.near_detractor}
          limit={6}
          variant="cause"
        />
        <CausesPanel
          title="Pasivos cerca de promotor (NPS=8)"
          items={data.near_promoter}
          limit={6}
          variant="strength"
        />
      </CardContent>
    </Card>
  );
}

export function NationalYTDPage() {
  const { data, isLoading, error } = useNationalYTD();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error al cargar vista nacional</CardTitle>
        </CardHeader>
        <CardContent>{error instanceof Error ? error.message : 'Error desconocido'}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Vista Nacional Year To Date</h1>
        <p className="text-sm text-muted-foreground">
          {formatInt(data.nps.total_responses)} respuestas · {formatInt(data.branches_total)} sucursales detectadas · {formatInt(data.branches_with_target)} con NPS objetivo configurado.
        </p>
        <SyntheticTargetsBanner />
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <NPSCard
          title="NPS nacional actual"
          value={data.nps.nps_actual}
          target={data.nps.nps_target}
          gap={data.nps.gap}
          tooltip="Polaridad inferida del NPS del cliente."
        />
        <NPSCard
          title="NPS objetivo nacional"
          value={data.nps.nps_target}
          showGap={false}
          caption="Promedio ponderado sintético."
        />
        <NPSCard
          title="Brecha vs objetivo"
          value={data.nps.gap}
          showGap={false}
          caption={data.nps.gap !== null && data.nps.gap < 0 ? 'Por debajo del objetivo.' : 'En o sobre el objetivo.'}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Distribución NPS</CardTitle>
          </CardHeader>
          <CardContent>
            <DistributionChart distribution={data.nps.distribution} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Tendencia mensual</CardTitle>
            <p className="text-xs text-muted-foreground">
              Últimos {data.trend.points.length} meses con respuestas.
            </p>
          </CardHeader>
          <CardContent>
            <TrendChart trend={data.trend} />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <CausesPanel
          title="Principales causas de fricción"
          items={data.causes}
          variant="cause"
          description="Buckets más mencionados por detractores YTD."
        />
        <StrengthsPanel
          title="Fortalezas mencionadas"
          items={data.strengths}
          description="Buckets más mencionados por promotores YTD."
        />
      </section>

      <CriticalBranchesTable branches={data.critical_branches} />

      <RankingsPanel rankings={data.rankings} />

      <ImpactSection items={data.impact} />

      <ActionsPanel actions={data.actions} />

      <PassiveSection />

      <InsightsList insights={data.insights} />
    </div>
  );
}
