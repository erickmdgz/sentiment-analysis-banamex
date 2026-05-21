import { Link } from 'react-router-dom';
import type { SuggestedAction } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PRIORITY_TONE, TONE_BG } from '@/lib/colors';
import { cn } from '@/lib/cn';

interface Props {
  actions: SuggestedAction[];
  title?: string;
  description?: string;
}

export function ActionsPanel({
  actions,
  title = 'Acciones sugeridas',
  description = 'Priorizadas por impacto estimado en NPS.',
}: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </CardHeader>
      <CardContent className="space-y-3">
        {actions.length === 0 && (
          <p className="text-sm text-muted-foreground">Sin acciones sugeridas todavía.</p>
        )}
        {actions.map((a, i) => {
          const tone = PRIORITY_TONE[a.priority];
          return (
            <div key={`${a.text}-${i}`} className="rounded-md border border-border p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm">{a.text}</p>
                <Badge variant="outline" className={cn('shrink-0 capitalize', TONE_BG[tone])}>
                  {a.priority}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {a.related_bucket && (
                  <Badge variant="neutral" className="text-[10px]">
                    {a.related_bucket}
                  </Badge>
                )}
                {a.related_branches.slice(0, 4).map((branchId) => (
                  <Link
                    key={branchId}
                    to={`/branches/${branchId}`}
                    className="text-primary hover:underline"
                  >
                    {branchId}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
