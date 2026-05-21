import { NavLink, Outlet, Navigate, Route, Routes, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Separator } from '@/components/ui/separator';
import { useAdminFiles, useAdminRuns } from '@/api/queries';
import { formatDate, formatInt, truncate } from '@/lib/format';
import { cn } from '@/lib/cn';

const SECTIONS = [
  { to: 'users', label: 'Gestión de usuarios' },
  { to: 'files', label: 'Cargas' },
  { to: 'runs', label: 'Validación de archivos' },
  { to: 'config', label: 'Configuración' },
  { to: 'monitoring', label: 'Monitoreo' },
  { to: 'logs', label: 'Logs' },
];

function AdminShell() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[200px_1fr]">
      <aside className="rounded-md border border-border bg-card p-2">
        <div className="px-2 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Administración
        </div>
        <Separator className="my-2" />
        <nav aria-label="Secciones de administración" className="flex flex-col gap-1">
          {SECTIONS.map((s) => (
            <NavLink
              key={s.to}
              to={s.to}
              className={({ isActive }) =>
                cn(
                  'rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              {s.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div>
        <Outlet />
      </div>
    </div>
  );
}

function Placeholder({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-sm text-muted-foreground">No implementado en MVP.</p>
      </CardHeader>
      <CardContent>
        <Link
          to="/national"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Volver a Vista CX
        </Link>
      </CardContent>
    </Card>
  );
}

function FilesPanel() {
  const { data, isLoading } = useAdminFiles();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cargas</CardTitle>
        <p className="text-xs text-muted-foreground">Histórico de archivos procesados (read-only).</p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Archivo</TableHead>
                <TableHead>SHA-256</TableHead>
                <TableHead className="text-right">Registros</TableHead>
                <TableHead>Subido</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((f) => (
                <TableRow key={f.id}>
                  <TableCell className="font-mono">{f.id}</TableCell>
                  <TableCell className="font-medium">{f.filename}</TableCell>
                  <TableCell className="font-mono text-[11px] text-muted-foreground">
                    {truncate(f.sha256, 12)}
                  </TableCell>
                  <TableCell className="text-right font-mono">{formatInt(f.rows_inserted)}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(f.uploaded_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function RunsPanel() {
  const { data, isLoading } = useAdminRuns();
  if (isLoading || !data) return <Skeleton className="h-48" />;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Corridas del anotador</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Modelo</TableHead>
                <TableHead className="text-right">Muestra</TableHead>
                <TableHead>Inicio</TableHead>
                <TableHead>Fin</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.annotation_runs.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono">{r.id}</TableCell>
                  <TableCell>{r.model}</TableCell>
                  <TableCell className="text-right font-mono">{formatInt(r.sample_size)}</TableCell>
                  <TableCell>{formatDate(r.started_at)}</TableCell>
                  <TableCell>{r.finished_at ? formatDate(r.finished_at) : '—'}</TableCell>
                  <TableCell className="capitalize">{r.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Corridas del clasificador</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Modelo</TableHead>
                <TableHead className="text-right">Muestras</TableHead>
                <TableHead className="text-right">F1 micro</TableHead>
                <TableHead className="text-right">F1 macro</TableHead>
                <TableHead className="text-right">Hamming</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.classifier_runs.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono">{r.id}</TableCell>
                  <TableCell className="font-mono text-[11px]">{r.model_path}</TableCell>
                  <TableCell className="text-right font-mono">{formatInt(r.n_samples)}</TableCell>
                  <TableCell className="text-right font-mono">{r.f1_micro?.toFixed(2) ?? '—'}</TableCell>
                  <TableCell className="text-right font-mono">{r.f1_macro?.toFixed(2) ?? '—'}</TableCell>
                  <TableCell className="text-right font-mono">{r.hamming_loss?.toFixed(2) ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export function AdminPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Administración</h1>
        <p className="text-sm text-muted-foreground">
          Vistas POC. Sección separada visualmente de la Vista CX.
        </p>
      </header>
      <Routes>
        <Route element={<AdminShell />}>
          <Route index element={<Navigate to="files" replace />} />
          <Route path="users" element={<Placeholder title="Gestión de usuarios" />} />
          <Route path="files" element={<FilesPanel />} />
          <Route path="runs" element={<RunsPanel />} />
          <Route path="config" element={<Placeholder title="Configuración" />} />
          <Route path="monitoring" element={<Placeholder title="Monitoreo" />} />
          <Route path="logs" element={<Placeholder title="Logs" />} />
        </Route>
      </Routes>
    </div>
  );
}
