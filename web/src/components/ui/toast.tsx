import * as React from 'react';
import { cn } from '@/lib/cn';

type ToastVariant = 'default' | 'success' | 'destructive';

interface Toast {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toasts: Toast[];
  push: (t: Omit<Toast, 'id'>) => void;
  dismiss: (id: number) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

let nextId = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const push = React.useCallback((t: Omit<Toast, 'id'>) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 5000);
  }, []);

  const dismiss = React.useCallback((id: number) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, push, dismiss }}>
      {children}
      <Toaster />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error('useToast debe usarse dentro de <ToastProvider>');
  return ctx;
}

function Toaster() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) return null;
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
      {ctx.toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={cn(
            'pointer-events-auto animate-fade-in rounded-md border bg-card p-4 shadow-lg',
            t.variant === 'success' && 'border-emerald-200 bg-emerald-50',
            t.variant === 'destructive' && 'border-rose-200 bg-rose-50',
          )}
        >
          <div className="text-sm font-semibold text-foreground">{t.title}</div>
          {t.description && <div className="mt-1 text-xs text-muted-foreground">{t.description}</div>}
        </div>
      ))}
    </div>
  );
}
