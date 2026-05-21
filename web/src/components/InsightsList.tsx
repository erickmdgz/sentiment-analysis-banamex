import {
  Activity,
  AlertOctagon,
  GaugeCircle,
  HeartHandshake,
  ListChecks,
  ShieldQuestion,
  Sparkles,
} from 'lucide-react';
import type { Insight } from '@/api/schema';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ICONS: Record<Insight['category'], React.ComponentType<{ className?: string }>> = {
  nps: GaugeCircle,
  brecha: AlertOctagon,
  fortaleza: Sparkles,
  fricción: ShieldQuestion,
  personal: HeartHandshake,
  comparación: Activity,
  cobertura: ListChecks,
};

interface Props {
  insights: Insight[];
  title?: string;
}

export function InsightsList({ insights, title = 'Insights generados' }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {insights.length === 0 && (
          <p className="text-sm text-muted-foreground">Sin insights disponibles.</p>
        )}
        {insights.map((insight, i) => {
          const Icon = ICONS[insight.category] ?? Activity;
          return (
            <div
              key={`${insight.text}-${i}`}
              className="flex gap-3 rounded-md border border-border p-3"
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
              <div>
                <p className="text-sm">{insight.text}</p>
                <p className="mt-0.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                  {insight.category}
                </p>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
