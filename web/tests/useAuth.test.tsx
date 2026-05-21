import { describe, expect, it, beforeEach, afterAll, beforeAll } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { TOKEN_KEY } from '@/api/client';
import { server } from '@/mocks/server';

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterAll(() => server.close());

function makeExpiredJwt() {
  const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' })).replace(/=+$/, '');
  const payload = btoa(JSON.stringify({ sub: 'demo', exp: 1 })).replace(/=+$/, '');
  return `${header}.${payload}.sig`;
}

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('arranca sin sesión', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated()).toBe(false);
    expect(result.current.token).toBeNull();
  });

  it('login persiste el token en localStorage', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.login('demo', 'pwd');
    });
    await waitFor(() => {
      expect(localStorage.getItem(TOKEN_KEY)).not.toBeNull();
      expect(result.current.isAuthenticated()).toBe(true);
    });
  });

  it('isAuthenticated devuelve false si exp expiró', () => {
    localStorage.setItem(TOKEN_KEY, makeExpiredJwt());
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated()).toBe(false);
  });

  it('logout borra el token', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.login('demo', 'pwd');
    });
    act(() => {
      result.current.logout();
    });
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(result.current.token).toBeNull();
  });
});
