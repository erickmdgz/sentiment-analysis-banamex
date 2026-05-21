import { Link } from 'react-router-dom';
import { ArrowLeft, GitCompareArrows } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { NPSCard } from '@/components/NPSCard';
import { DistributionChart } from '@/components/DistributionChart';
import { TrendChart } from '@/components/TrendChart';
import { CausesPanel } from '@/components/CausesPanel';
import { StrengthsPanel } from '@/components/StrengthsPanel';
import { ActionsPanel } from '@/components/ActionsPanel';
import { InsightsList } from '@/components/InsightsList';
import { SyntheticTargetsBanner } from '@/components/SyntheticTargetsBanner';
import { WordsCloud } from '@/components/WordsCloud';
import { RepresentativeComments } from '@/components/RepresentativeComments';
import { PersonnelTable } from '@/components/PersonnelTable';
import { useBranchYTD, useCriticalBranches } from '@/api/queries';
import { useBranch } from '@/hooks/useBranch';
import { ApiError } from '@/api/client';

export function BranchYTDPage() {
  const branchId = useBranch();
  const branch = useBranchYTD(branchId);
  const critical = useCriticalBranches(20);

  if (!branchId) {
    return <Skeleton className="h-32" />;
  }

  if (branch.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (branch.error instanceof ApiError && branch.error.status === 404) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sucursal no encontrada</CardTitle>
          <p className="text-sm text-muted-foreground">
            El identificador {branchId} no existe en la base actual.
          </p>
        </CardHeader>
        <CardContent>
          <Link
            to="/branches"
            className="inline-flex h-10 items-center gap-2 rounded-md border border-input bg-background px-4 text-sm font-medium hover:bg-accent"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Volver al selector
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (branch.error || !branch.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error al cargar la sucursal</CardTitle>
        </CardHeader>
        <CardContent>{branch.error instanceof Error ? branch.error.message : 'Error desconocido'}</CardContent>
      </Card>
    );
  }

  const data = branch.data;
  const isCritical = critical.data?.some((c) => c.branch_id === branchId) ?? false;
  const hasTarget = data.nps.nps_target !== null;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">Sucursal {branchId}</h1>
          {isCritical && <Badge variant="danger">Crítica</Badge>}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>{data.nps.total_responses} respuestas YTD</span>
          <span>·</span>
          <Link to={`/branches/${branchId}/compare`} className="inline-flex items-center gap-1 text-primary hover:underline">
            <GitCompareArrows className="h-4 w-4" aria-hidden />
            Comparar meses
          </Link>
        </div>
        {hasTarget ? (
          <SyntheticTargetsBanner />
        ) : (
          <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            Esta sucursal no tiene NPS objetivo configurado en la fuente interna.
          </div>
        )}
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <NPSCard
          title="NPS actual"
          value={data.nps.nps_actual}
          target={data.nps.nps_target}
          gap={data.nps.gap}
          tooltip="Polaridad inferida del NPS del cliente."
        />
        <NPSCard
          title="NPS objetivo"
          value={data.nps.nps_target}
          showGap={false}
          caption={hasTarget ? 'Sintético — para demo.' : 'Sin objetivo configurado.'}
        />
        <NPSCard
          title="Brecha"
          value={data.nps.gap}
          showGap={false}
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
          </CardHeader>
          <CardContent>
            <TrendChart trend={data.trend} />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <CausesPanel
          title="Principales causas"
          items={data.causes}
          variant="cause"
        />
        <StrengthsPanel
          items={data.strengths}
        />
      </section>

      <ActionsPanel actions={data.actions} />

      <WordsCloud branchId={branchId} />

      <RepresentativeComments comments={data.representatives} />

      <PersonnelTable personnel={data.personnel} />

      <InsightsList insights={data.insights} />
    </div>
  );
}
