import { useNavigate } from 'react-router-dom';
import { useBranchesList, useCriticalBranches } from '@/api/queries';
import { Combobox, type ComboboxItem } from '@/components/ui/combobox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

interface Props {
  selected: string | null;
  onSelect: (branchId: string) => void;
}

export function BranchSelector({ selected, onSelect }: Props) {
  const navigate = useNavigate();
  const { data: branches, isLoading } = useBranchesList();
  const { data: critical } = useCriticalBranches(8);

  const items: ComboboxItem[] = (branches ?? []).map((b) => ({
    value: b.branch_id,
    label: b.branch_id,
    hint: `${b.response_count} respuestas${b.has_target ? '' : ' · sin objetivo'}`,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Buscar sucursal</CardTitle>
        <p className="text-xs text-muted-foreground">
          {branches?.length
            ? `${branches.length.toLocaleString('es-MX')} sucursales detectadas. Escribe para filtrar.`
            : 'Cargando catálogo de sucursales…'}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {critical && critical.length > 0 && (
          <div>
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Sucursales críticas
            </div>
            <div className="flex flex-wrap gap-2">
              {critical.slice(0, 8).map((b) => (
                <Button
                  key={b.branch_id}
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/branches/${b.branch_id}`)}
                  className="h-7 gap-2 text-xs"
                >
                  {b.branch_id}
                  {b.gap !== null && (
                    <Badge variant="danger" className="text-[10px]">
                      {b.gap.toFixed(1)}
                    </Badge>
                  )}
                </Button>
              ))}
            </div>
          </div>
        )}
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <Combobox
            items={items}
            value={selected}
            onChange={onSelect}
            placeholder="Buscar por código (ej. A-0012)…"
            maxVisible={80}
          />
        )}
      </CardContent>
    </Card>
  );
}
