import { Link } from 'react-router-dom';
import type { CriticalBranch } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { gapTone, TONE_BG } from '@/lib/colors';
import { formatNPS, formatPct } from '@/lib/format';
import { cn } from '@/lib/cn';

interface Props {
  branches: CriticalBranch[];
  title?: string;
  description?: string;
}

export function CriticalBranchesTable({
  branches,
  title = 'Sucursales críticas',
  description = 'Top 10 con mayor brecha y/o detractores.',
}: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sucursal</TableHead>
              <TableHead className="text-right">NPS</TableHead>
              <TableHead className="text-right">Objetivo</TableHead>
              <TableHead className="text-right">Brecha</TableHead>
              <TableHead className="text-right">% detractores</TableHead>
              <TableHead>Condición</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {branches.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-sm text-muted-foreground">
                  Sin sucursales críticas.
                </TableCell>
              </TableRow>
            )}
            {branches.map((b) => {
              const tone = gapTone(b.gap ?? null);
              return (
                <TableRow key={b.branch_id}>
                  <TableCell>
                    <Link to={`/branches/${b.branch_id}`} className="font-medium text-primary hover:underline">
                      {b.branch_id}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">{formatNPS(b.nps_actual)}</TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {b.nps_target !== null ? formatNPS(b.nps_target) : '—'}
                  </TableCell>
                  <TableCell className="text-right">
                    {b.gap !== null ? (
                      <Badge variant="outline" className={cn('border', TONE_BG[tone])}>
                        {formatNPS(b.gap)}
                      </Badge>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {formatPct(b.detractors_pct)}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {b.triggered_conditions.slice(0, 4).map((cond, i) => (
                        <Badge key={`${b.branch_id}-${i}`} variant="neutral" className="text-[10px]">
                          {cond}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
