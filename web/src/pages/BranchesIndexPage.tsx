import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BranchSelector } from '@/components/BranchSelector';

export function BranchesIndexPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = React.useState<string | null>(null);
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Sucursales</h1>
        <p className="text-sm text-muted-foreground">
          Selecciona una sucursal para ver su detalle granular YTD.
        </p>
      </header>
      <BranchSelector
        selected={selected}
        onSelect={(id) => {
          setSelected(id);
          navigate(`/branches/${id}`);
        }}
      />
      {!selected && (
        <Card>
          <CardHeader>
            <CardTitle>Selecciona una sucursal</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Usa el buscador o las sucursales críticas para abrir la vista granular.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
