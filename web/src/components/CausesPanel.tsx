import type { CauseBucket } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/cn';
import { formatInt, formatPct } from '@/lib/format';

interface Props {
  title: string;
  items: CauseBucket[];
  variant?: 'cause' | 'strength';
  limit?: number;
  description?: string;
}

export function CausesPanel({ title, items, variant = 'cause', limit = 8, description }: Props) {
  const sorted = [...items].sort((a, b) => b.count - a.count).slice(0, limit);
  const max = sorted.reduce((acc, b) => Math.max(acc, b.count), 1);
  const isCause = variant === 'cause';
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </CardHeader>
      <CardContent className="space-y-3">
        {sorted.length === 0 && (
          <p className="text-sm text-muted-foreground">Sin datos disponibles.</p>
        )}
        {sorted.map((b) => {
          const w = (b.count / max) * 100;
          return (
            <div key={b.bucket} className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{b.bucket}</span>
                <div className="flex items-center gap-2">
                  <Badge variant="neutral" className="font-mono text-[10px]">
                    {formatInt(b.count)}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    {formatPct(b.pct_of_group)}
                  </Badge>
                </div>
              </div>
              <div className="h-2 w-full rounded-full bg-muted">
                <div
                  className={cn('h-full rounded-full', isCause ? 'bg-banamex-red/80' : 'bg-banamex-green/80')}
                  style={{ width: `${w}%` }}
                />
              </div>
              {b.sample_l2.length > 0 && (
                <p className="text-[11px] text-muted-foreground">
                  {b.sample_l2.slice(0, 3).join(' · ')}
                </p>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
