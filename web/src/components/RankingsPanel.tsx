import { Link } from 'react-router-dom';
import type { Ranking, Rankings } from '@/api/schema';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const TABS: Array<{ key: keyof Rankings; label: string }> = [
  { key: 'worst_nps', label: 'Peor NPS' },
  { key: 'worst_gap', label: 'Mayor brecha' },
  { key: 'most_detractors', label: '% detractores' },
  { key: 'worsened', label: 'Empeoraron' },
  { key: 'improved', label: 'Mejoraron' },
];

interface Props {
  rankings: Rankings;
}

function RankingTable({ ranking }: { ranking: Ranking }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Sucursal</TableHead>
          <TableHead className="text-right">Valor</TableHead>
          <TableHead>Etiqueta</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {ranking.items.map((item) => (
          <TableRow key={item.branch_id}>
            <TableCell>
              <Link to={`/branches/${item.branch_id}`} className="font-medium text-primary hover:underline">
                {item.branch_id}
              </Link>
            </TableCell>
            <TableCell className="text-right font-mono">{item.value.toFixed(1)}</TableCell>
            <TableCell className="text-xs text-muted-foreground">{item.label}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function RankingsPanel({ rankings }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Rankings nacionales</CardTitle>
        <p className="text-xs text-muted-foreground">Top 5 por categoría — datos YTD.</p>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue={TABS[0].key as string}>
          <TabsList className="flex w-full flex-wrap gap-1">
            {TABS.map((t) => (
              <TabsTrigger key={t.key} value={t.key as string}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {TABS.map((t) => (
            <TabsContent key={t.key} value={t.key as string}>
              <RankingTable ranking={rankings[t.key]} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
