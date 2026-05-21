import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { TOKEN_KEY, apiClient } from '@/api/client';
import type { LoginResponse } from '@/api/schema';

interface JWTPayload {
  sub?: string;
  exp?: number;
}

function decodeJwt(token: string | null): JWTPayload | null {
  if (!token) return null;
  try {
    const [, payload] = token.split('.');
    if (!payload) return null;
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as JWTPayload;
  } catch {
    return null;
  }
}

interface UseAuthReturn {
  token: string | null;
  username: string | null;
  isAuthenticated: () => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export function useAuth(): UseAuthReturn {
  const [token, setToken] = React.useState<string | null>(() =>
    typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null,
  );
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const refresh = React.useCallback(() => {
    setToken(localStorage.getItem(TOKEN_KEY));
  }, []);

  React.useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === TOKEN_KEY) refresh();
    }
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [refresh]);

  const isAuthenticated = React.useCallback(() => {
    const current = token ?? localStorage.getItem(TOKEN_KEY);
    if (!current) return false;
    const payload = decodeJwt(current);
    if (!payload?.exp) return Boolean(current);
    return Date.now() / 1000 < payload.exp;
  }, [token]);

  const username = React.useMemo(() => {
    const payload = decodeJwt(token);
    return payload?.sub ?? null;
  }, [token]);

  const login = React.useCallback(
    async (user: string, password: string) => {
      const res = await apiClient.post<LoginResponse>('/auth/login', {
        username: user,
        password,
      });
      localStorage.setItem(TOKEN_KEY, res.token);
      setToken(res.token);
    },
    [],
  );

  const logout = React.useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    queryClient.clear();
    navigate('/login', { replace: true });
  }, [navigate, queryClient]);

  return { token, username, isAuthenticated, login, logout };
}
