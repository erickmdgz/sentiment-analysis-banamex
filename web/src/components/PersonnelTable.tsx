import type { PersonnelMention } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { truncate } from '@/lib/format';

interface Props {
  personnel: PersonnelMention[];
}

export function PersonnelTable({ personnel }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Personal mencionado</CardTitle>
        <p className="text-xs text-muted-foreground">
          Nombres extraídos por extractor rule-based. Polaridad inferida del contexto.
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Polaridad</TableHead>
              <TableHead className="text-right">Menciones</TableHead>
              <TableHead>Ejemplo</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {personnel.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-sm text-muted-foreground">
                  Sin menciones de personal.
                </TableCell>
              </TableRow>
            )}
            {personnel.map((p) => (
              <TableRow key={`${p.name}-${p.example_record_id}`}>
                <TableCell className="font-medium">{p.name}</TableCell>
                <TableCell>
                  <Badge variant={p.polarity === 'pos' ? 'success' : 'danger'} className="capitalize">
                    {p.polarity === 'pos' ? 'positiva' : 'negativa'}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-mono">{p.count}</TableCell>
                <TableCell className="text-xs italic text-muted-foreground">
                  “{truncate(p.example_verbatim, 90)}”
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
