import * as React from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/api/client';
import type { ValidationSummary } from '@/api/schema';

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  if (auth.isAuthenticated()) {
    return <Navigate to="/national" replace />;
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await auth.login(username.trim() || 'demo', password);
      const validation = await queryClient.fetchQuery<ValidationSummary>({
        queryKey: ['validation'],
        queryFn: () => apiClient.get<ValidationSummary>('/validation'),
      });
      const target =
        (location.state as { from?: string } | null)?.from ??
        (validation.rows_loaded === 0 ? '/upload' : '/national');
      navigate(target, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-md bg-banamex-red text-white text-lg font-bold">
            Bx
          </div>
          <CardTitle>Banamex CX</CardTitle>
          <CardDescription>Análisis de sentimientos en sucursales</CardDescription>
        </CardHeader>
        <form onSubmit={onSubmit}>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="username">Usuario</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                autoComplete="username"
                placeholder="demo"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password">Contraseña</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="••••"
              />
            </div>
            {error && (
              <p role="alert" className="text-xs text-destructive">
                {error}
              </p>
            )}
          </CardContent>
          <CardFooter className="flex flex-col gap-2">
            <Button type="submit" className="w-full" disabled={submitting}>
              <LogIn className="h-4 w-4" aria-hidden />
              {submitting ? 'Entrando…' : 'Entrar'}
            </Button>
            <p className="text-center text-[11px] text-muted-foreground">
              Demo del Hackathon Banamex CX — autenticación simulada.
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
