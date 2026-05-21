import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/cn';

interface Props {
  className?: string;
}

export function SyntheticTargetsBanner({ className }: Props) {
  return (
    <div
      role="note"
      className={cn(
        'flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900',
        className,
      )}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden />
      <p>
        <span className="font-semibold">Objetivos NPS sintéticos para demo.</span>{' '}
        Los valores objetivo se generaron internamente porque el cliente del reto no
        entregó NPS objetivo real por sucursal.
      </p>
    </div>
  );
}
