import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Upload, FileText, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useCoverage, useUploadFile, useUploadStatus, useValidation } from '@/api/queries';
import { useToast } from '@/components/ui/toast';
import type { UploadResponse, ValidationSummary } from '@/api/schema';
import { formatInt } from '@/lib/format';
import { cn } from '@/lib/cn';

interface UploadEntry {
  file: File;
  status: 'queued' | 'uploading' | 'parsing' | 'classifying' | 'done' | 'error';
  progress: number;
  message?: string;
  fileId?: number;
}

function StatusItem({ entry }: { entry: UploadEntry }) {
  const isFinal = entry.status === 'done' || entry.status === 'error';
  const { data } = useUploadStatus(entry.fileId ?? null, { polling: !isFinal });
  const status = data?.status ?? entry.status;
  const progress = data ? Math.round(data.progress * 100) : Math.round(entry.progress * 100);
  return (
    <div className="rounded-md border border-border p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" aria-hidden />
          <div>
            <div className="text-sm font-medium">{entry.file.name}</div>
            <div className="text-[11px] text-muted-foreground">
              {formatInt(Math.round(entry.file.size / 1024))} KB
            </div>
          </div>
        </div>
        <Badge
          variant={
            status === 'done' ? 'success' : status === 'error' ? 'danger' : 'warning'
          }
          className="capitalize"
        >
          {status}
        </Badge>
      </div>
      <Progress value={progress} className="mt-3" />
    </div>
  );
}

function ValidationCard({ summary }: { summary: ValidationSummary }) {
  const rows = [
    ['Archivos procesados', summary.files_processed],
    ['Registros cargados', summary.rows_loaded],
    ['Nuevos', summary.rows_new],
    ['Duplicados ignorados', summary.rows_duplicated_ignored],
    ['Sucursales detectadas', summary.branches_detected],
    ['Periodo disponible', summary.period_available.join(' → ')],
    ['Meses disponibles', summary.months_available.length],
    ['Columnas detectadas', summary.columns_detected.length],
    ['Registros válidos', summary.rows_valid],
    ['Verbalización vacía', summary.rows_empty_verbatim],
    ['NPS inválido', summary.rows_invalid_nps],
    ['Sin branch', summary.rows_missing_branch],
    ['Duplicados record_id', summary.rows_duplicate_record_id],
    ['Fechas inválidas', summary.rows_invalid_date],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Resumen de validación</CardTitle>
        <p className="text-xs text-muted-foreground">
          Agregado de todos los archivos cargados desde el último reset.
        </p>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-3">
          {rows.map(([label, value]) => (
            <div key={label as string} className="rounded-md border border-border p-2">
              <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</dt>
              <dd className="mt-0.5 font-mono text-sm">
                {typeof value === 'number' ? formatInt(value) : value}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function CoverageCard() {
  const { data, isLoading } = useCoverage();
  const [expanded, setExpanded] = React.useState<'none' | 'without' | 'no_responses'>('none');
  if (isLoading) return <Skeleton className="h-40" />;
  if (!data) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cobertura de objetivos</CardTitle>
        <p className="text-xs text-muted-foreground">
          Cruce entre sucursales detectadas en encuestas y catálogo de objetivos.
        </p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <Stat label="Detectadas" value={data.branches_detected} />
          <Stat label="Con objetivo" value={data.branches_with_target} />
          <Stat label="Sin objetivo" value={data.branches_without_target.length} />
          <Stat label="Sin respuestas" value={data.branches_with_target_no_responses.length} />
        </div>
        <CollapsibleList
          label="Sucursales sin objetivo"
          items={data.branches_without_target}
          open={expanded === 'without'}
          onToggle={() => setExpanded((prev) => (prev === 'without' ? 'none' : 'without'))}
        />
        <CollapsibleList
          label="Sucursales con objetivo pero sin respuestas"
          items={data.branches_with_target_no_responses}
          open={expanded === 'no_responses'}
          onToggle={() => setExpanded((prev) => (prev === 'no_responses' ? 'none' : 'no_responses'))}
        />
        {data.invalid_targets.length > 0 && (
          <p className="text-xs text-rose-700">
            Objetivos inválidos: {data.invalid_targets.length}
          </p>
        )}
        {data.duplicate_targets.length > 0 && (
          <p className="text-xs text-rose-700">
            Objetivos duplicados: {data.duplicate_targets.length}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-border bg-muted/40 p-2">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono text-base">{typeof value === 'number' ? formatInt(value) : value}</div>
    </div>
  );
}

function CollapsibleList({
  label,
  items,
  open,
  onToggle,
}: {
  label: string;
  items: string[];
  open: boolean;
  onToggle: () => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="rounded-md border border-border">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium"
      >
        <span>{label}</span>
        <Badge variant="neutral">{formatInt(items.length)}</Badge>
      </button>
      {open && (
        <div className="max-h-40 overflow-y-auto border-t border-border p-2">
          <div className="flex flex-wrap gap-1">
            {items.slice(0, 200).map((id) => (
              <Badge key={id} variant="outline" className="text-[10px] font-mono">
                {id}
              </Badge>
            ))}
            {items.length > 200 && (
              <span className="text-[11px] text-muted-foreground">
                +{formatInt(items.length - 200)} más…
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function UploadPage() {
  const [entries, setEntries] = React.useState<UploadEntry[]>([]);
  const [dragOver, setDragOver] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const upload = useUploadFile();
  const validation = useValidation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();

  async function handleFiles(files: FileList | null) {
    if (!files) return;
    const accepted = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.txt'));
    if (accepted.length === 0) {
      toast.push({ title: 'Sólo se aceptan archivos .txt', variant: 'destructive' });
      return;
    }
    for (const file of accepted) {
      setEntries((prev) => [
        ...prev,
        { file, status: 'uploading', progress: 0.05 },
      ]);
      try {
        const res: UploadResponse = await upload.mutateAsync(file);
        setEntries((prev) =>
          prev.map((e) =>
            e.file === file
              ? { ...e, status: 'parsing', progress: 0.2, fileId: res.file_id }
              : e,
          ),
        );
        toast.push({
          title: `Archivo ${file.name} en proceso`,
          description: `${formatInt(res.validation_summary.rows_loaded)} registros válidos totales.`,
          variant: 'success',
        });
      } catch (err) {
        setEntries((prev) =>
          prev.map((e) =>
            e.file === file
              ? {
                  ...e,
                  status: 'error',
                  progress: 1,
                  message: err instanceof Error ? err.message : 'Error',
                }
              : e,
          ),
        );
        toast.push({ title: 'No se pudo subir el archivo', description: file.name, variant: 'destructive' });
      }
    }
    queryClient.invalidateQueries({ queryKey: ['validation'] });
    queryClient.invalidateQueries({ queryKey: ['validation', 'coverage'] });
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Carga de archivos NPS</h1>
        <p className="text-sm text-muted-foreground">
          Sube archivos de encuestas en formato .txt. La validación se ejecuta automáticamente.
        </p>
      </header>

      <Card>
        <CardContent className="p-0">
          <label
            htmlFor="file-input"
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              void handleFiles(e.dataTransfer.files);
            }}
            className={cn(
              'flex h-64 cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed text-center transition-colors',
              dragOver ? 'border-primary bg-primary/5' : 'border-border bg-muted/20',
            )}
          >
            <Upload className="h-10 w-10 text-muted-foreground" aria-hidden />
            <div>
              <div className="text-sm font-medium">
                Arrastra archivos .txt aquí o haz clic para seleccionar
              </div>
              <div className="text-xs text-muted-foreground">
                Acepta múltiples archivos. Tamaño máximo 50 MB cada uno.
              </div>
            </div>
            <input
              id="file-input"
              ref={inputRef}
              type="file"
              accept=".txt"
              multiple
              hidden
              onChange={(e) => {
                void handleFiles(e.target.files);
                e.target.value = '';
              }}
            />
          </label>
        </CardContent>
      </Card>

      {entries.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Cola de carga</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setEntries([])}>
              <Trash2 className="h-4 w-4" aria-hidden />
              Limpiar
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {entries.map((e) => (
              <StatusItem key={`${e.file.name}-${e.file.lastModified}`} entry={e} />
            ))}
          </CardContent>
        </Card>
      )}

      {validation.data && <ValidationCard summary={validation.data} />}
      <CoverageCard />

      <div className="flex justify-end">
        <Button
          onClick={() => {
            queryClient.invalidateQueries({ queryKey: ['national'] });
            queryClient.invalidateQueries({ queryKey: ['branches'] });
            navigate('/national');
          }}
        >
          Continuar a vista nacional
        </Button>
      </div>
    </div>
  );
}
