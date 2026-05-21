import { Outlet, useLocation, useMatch } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sidebar } from './Sidebar';
import { useAuth } from '@/hooks/useAuth';

interface Crumb {
  label: string;
  path?: string;
}

function useCrumbs(): Crumb[] {
  const location = useLocation();
  const branchMatch = useMatch('/branches/:branchId/*');
  const segments = location.pathname.split('/').filter(Boolean);
  const crumbs: Crumb[] = [];

  if (segments[0] === 'upload') {
    crumbs.push({ label: 'Carga' });
  } else if (segments[0] === 'national') {
    crumbs.push({ label: 'Nacional', path: '/national' });
    if (segments[1] === 'compare') crumbs.push({ label: 'Comparación' });
  } else if (segments[0] === 'branches') {
    crumbs.push({ label: 'Sucursales', path: '/branches' });
    if (branchMatch?.params.branchId) {
      crumbs.push({ label: branchMatch.params.branchId, path: `/branches/${branchMatch.params.branchId}` });
    }
    if (segments[2] === 'compare') crumbs.push({ label: 'Comparación' });
  } else if (segments[0] === 'admin') {
    crumbs.push({ label: 'Administración', path: '/admin' });
    if (segments[1]) {
      const map: Record<string, string> = {
        users: 'Usuarios',
        files: 'Cargas',
        runs: 'Validación',
        config: 'Configuración',
        monitoring: 'Monitoreo',
        logs: 'Logs',
      };
      crumbs.push({ label: map[segments[1]] ?? segments[1] });
    }
  } else {
    crumbs.push({ label: 'Inicio' });
  }
  return crumbs;
}

export function Layout() {
  const auth = useAuth();
  const crumbs = useCrumbs();
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4">
          <nav aria-label="breadcrumbs" className="flex items-center gap-2 text-sm">
            {crumbs.map((crumb, i) => (
              <span key={`${crumb.label}-${i}`} className="flex items-center gap-2 text-muted-foreground">
                {i > 0 && <span aria-hidden>/</span>}
                <span className={i === crumbs.length - 1 ? 'font-medium text-foreground' : ''}>
                  {crumb.label}
                </span>
              </span>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">
              {auth.username ? <>Sesión: <span className="font-medium text-foreground">{auth.username}</span></> : 'Demo'}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={auth.logout}
              aria-label="Cerrar sesión"
            >
              <LogOut className="h-4 w-4" aria-hidden />
              Salir
            </Button>
          </div>
        </header>
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6 md:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
