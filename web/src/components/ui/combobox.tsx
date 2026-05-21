import * as React from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Input } from './input';

export interface ComboboxItem {
  value: string;
  label: string;
  hint?: string;
}

export interface ComboboxProps {
  items: ComboboxItem[];
  value: string | null;
  onChange: (value: string) => void;
  placeholder?: string;
  emptyLabel?: string;
  className?: string;
  maxVisible?: number;
}

// Combobox controlado con filtro local. Para no pintar 1,291 nodos a la vez,
// limita la cantidad de items renderizados a `maxVisible` (default 50).
export function Combobox({
  items,
  value,
  onChange,
  placeholder = 'Buscar…',
  emptyLabel = 'Sin resultados',
  className,
  maxVisible = 50,
}: ComboboxProps) {
  const [query, setQuery] = React.useState('');

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items.slice(0, maxVisible);
    return items
      .filter(
        (item) =>
          item.value.toLowerCase().includes(q) || item.label.toLowerCase().includes(q),
      )
      .slice(0, maxVisible);
  }, [items, query, maxVisible]);

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          aria-label="Buscar sucursal"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-9"
        />
      </div>
      <ul
        role="listbox"
        aria-label="Sucursales"
        className="mt-2 max-h-72 overflow-y-auto rounded-md border border-border bg-card divide-y divide-border"
      >
        {filtered.length === 0 && (
          <li className="p-4 text-sm text-muted-foreground">{emptyLabel}</li>
        )}
        {filtered.map((item) => {
          const selected = value === item.value;
          return (
            <li key={item.value} role="option" aria-selected={selected}>
              <button
                type="button"
                onClick={() => onChange(item.value)}
                className={cn(
                  'flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-muted/60',
                  selected && 'bg-primary/10 text-primary',
                )}
              >
                <span className="font-medium">{item.label}</span>
                {item.hint && (
                  <span className="text-xs text-muted-foreground">{item.hint}</span>
                )}
              </button>
            </li>
          );
        })}
        {!query && items.length > maxVisible && (
          <li className="px-3 py-2 text-xs text-muted-foreground">
            Mostrando los primeros {maxVisible} resultados. Escribe para filtrar entre {items.length.toLocaleString('es-MX')} sucursales.
          </li>
        )}
      </ul>
    </div>
  );
}
