import * as React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useBranchWords } from '@/api/queries';
import type { WordFrequency } from '@/api/schema';

interface Props {
  branchId: string;
  title?: string;
}

function WordsTable({ items, isLoading }: { items?: WordFrequency[]; isLoading: boolean }) {
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando…</p>;
  }
  if (!items || items.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin palabras suficientes para mostrar.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Palabra</TableHead>
          <TableHead className="text-right">Frecuencia</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.slice(0, 30).map((w) => (
          <TableRow key={w.word}>
            <TableCell className="font-medium">{w.word}</TableCell>
            <TableCell className="text-right font-mono">{w.count}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

const TABS: Array<{ value: string; label: string; group: string | null }> = [
  { value: 'general', label: 'General', group: null },
  { value: 'promoter', label: 'Promotores', group: 'Promotor' },
  { value: 'detractor', label: 'Detractores', group: 'Detractor' },
];

export function WordsCloud({ branchId, title = 'Palabras frecuentes' }: Props) {
  const [active, setActive] = React.useState('general');
  const tab = TABS.find((t) => t.value === active) ?? TABS[0];
  const { data, isLoading } = useBranchWords(branchId, tab.group, 30);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-xs text-muted-foreground">
          Tabla en lugar de nube — manteniendo legibilidad en pantallas chicas.
        </p>
      </CardHeader>
      <CardContent>
        <Tabs value={active} onValueChange={setActive} defaultValue={active}>
          <TabsList className="flex flex-wrap gap-1">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {TABS.map((t) => (
            <TabsContent key={t.value} value={t.value}>
              <WordsTable items={data} isLoading={isLoading} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
