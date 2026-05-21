import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthGuard } from '@/components/AuthGuard';
import { TOKEN_KEY } from '@/api/client';
import { makeFakeJWT } from '@/mocks/fixtures';

function renderGuarded(initial: string) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/login" element={<div>Login screen</div>} />
          <Route
            path="/national"
            element={
              <AuthGuard>
                <div>Vista nacional</div>
              </AuthGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AuthGuard', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('redirige a /login si no hay token', () => {
    renderGuarded('/national');
    expect(screen.getByText('Login screen')).toBeInTheDocument();
    expect(screen.queryByText('Vista nacional')).toBeNull();
  });

  it('renderiza children cuando hay token válido', () => {
    localStorage.setItem(TOKEN_KEY, makeFakeJWT('demo').token);
    renderGuarded('/national');
    expect(screen.getByText('Vista nacional')).toBeInTheDocument();
  });
});
