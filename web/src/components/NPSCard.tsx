import { ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/cn';
import { gapTone, TONE_BG, TONE_DOT, TONE_TEXT } from '@/lib/colors';
import { formatNPS } from '@/lib/format';

interface NPSCardProps {
  title: string;
  value: number | null | undefined;
  target?: number | null;
  gap?: number | null;
  caption?: string;
  showGap?: boolean;
  tooltip?: string;
}

export function NPSCard({ title, value, target, gap, caption, showGap = true, tooltip }: NPSCardProps) {
  const tone = gapTone(gap ?? null);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-sm font-medium text-muted-foreground">
          {title}
          <span className={cn('h-2 w-2 rounded-full', TONE_DOT[tone])} aria-hidden />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={cn('text-4xl font-semibold tracking-tight', TONE_TEXT[tone])}>
          {formatNPS(value ?? null)}
        </div>
        {tooltip && (
          <div className="mt-1 text-xs text-muted-foreground">{tooltip}</div>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {target !== undefined && target !== null && (
            <span className="inline-flex items-center gap-1">
              <span>Objetivo:</span>
              <span className="font-medium text-foreground">{formatNPS(target)}</span>
            </span>
          )}
          {showGap && gap !== undefined && gap !== null && (
            <Badge
              variant="outline"
              className={cn('border', TONE_BG[tone])}
              aria-label={`Brecha ${gap}`}
            >
              <ArrowRight className="mr-1 h-3 w-3" aria-hidden />
              Brecha {formatNPS(gap)}
            </Badge>
          )}
        </div>
        {caption && <div className="mt-3 text-xs text-muted-foreground">{caption}</div>}
      </CardContent>
    </Card>
  );
}
