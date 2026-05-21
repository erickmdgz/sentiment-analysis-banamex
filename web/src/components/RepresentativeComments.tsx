import type { RepresentativeComment } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/format';

interface Props {
  comments: RepresentativeComment[];
}

const TONE: Record<RepresentativeComment['nps_group'], 'success' | 'warning' | 'danger'> = {
  Promotor: 'success',
  Pasivo: 'warning',
  Detractor: 'danger',
};

export function RepresentativeComments({ comments }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Comentarios representativos</CardTitle>
        <p className="text-xs text-muted-foreground">
          Dos comentarios por bucket — seleccionados por relevancia semántica.
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        {comments.length === 0 && (
          <p className="text-sm text-muted-foreground">Sin comentarios disponibles.</p>
        )}
        {comments.map((c) => (
          <div key={c.record_id} className="rounded-md border border-border p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="text-[10px]">
                {c.bucket}
              </Badge>
              <Badge variant={TONE[c.nps_group]} className="text-[10px]">
                {c.nps_group}
              </Badge>
              <span className="font-mono">NPS {c.nps_rate}</span>
              <span>·</span>
              <span>{formatDate(c.response_date)}</span>
            </div>
            <blockquote className="border-l-2 border-border pl-3 text-sm italic">
              {c.verbatim}
            </blockquote>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
