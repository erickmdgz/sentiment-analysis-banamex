import { NavLink } from 'react-router-dom';
import {
  Upload as UploadIcon,
  BarChart3,
  GitCompareArrows,
  Building2,
  FileSpreadsheet,
  Activity,
  Sliders,
  Gauge,
  ScrollText,
  Users,
  ShieldCheck,
} from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/cn';

interface SidebarLinkProps {
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  end?: boolean;
}

function SidebarLink({ to, icon: Icon, label, end }: SidebarLinkProps) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )
      }
    >
      <Icon className="h-4 w-4" aria-hidden />
      <span>{label}</span>
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden h-full w-60 shrink-0 flex-col border-r border-border bg-card md:flex">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="grid h-9 w-9 place-items-center rounded-md bg-banamex-red text-white text-sm font-bold">
          Bx
        </div>
        <div>
          <div className="text-sm font-semibold leading-none">Banamex CX</div>
          <div className="text-xs text-muted-foreground">Análisis NPS</div>
        </div>
      </div>
      <Separator />
      <nav aria-label="Navegación principal" className="flex flex-1 flex-col gap-1 px-3 py-4">
        <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Vista CX
        </div>
        <SidebarLink to="/upload" icon={UploadIcon} label="Carga de archivos" />
        <SidebarLink to="/national" icon={BarChart3} label="Vista Nacional" end />
        <SidebarLink to="/national/compare" icon={GitCompareArrows} label="Comparación Nacional" />
        <SidebarLink to="/branches" icon={Building2} label="Sucursales" end />
        <Separator className="my-3" />
        <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Administración
        </div>
        <SidebarLink to="/admin/users" icon={Users} label="Gestión de usuarios" />
        <SidebarLink to="/admin/files" icon={FileSpreadsheet} label="Cargas" />
        <SidebarLink to="/admin/runs" icon={Activity} label="Validación de archivos" />
        <SidebarLink to="/admin/config" icon={Sliders} label="Configuración" />
        <SidebarLink to="/admin/monitoring" icon={Gauge} label="Monitoreo" />
        <SidebarLink to="/admin/logs" icon={ScrollText} label="Logs" />
      </nav>
      <Separator />
      <div className="flex items-center gap-2 px-5 py-3 text-xs text-muted-foreground">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        <span>Demo Hackathon · Tec Monterrey</span>
      </div>
    </aside>
  );
}
