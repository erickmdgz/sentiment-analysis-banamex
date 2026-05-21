import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { server } from '@/mocks/server';
import { NationalYTDPage } from '@/pages/NationalYTDPage';
import { TOKEN_KEY } from '@/api/client';
import { makeFakeJWT } from '@/mocks/fixtures';

import { beforeEach } from 'vitest';
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
beforeEach(() => {
  localStorage.setItem(TOKEN_KEY, makeFakeJWT('demo').token);
});
afterAll(() => server.close());

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/national']}>
        <NationalYTDPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('NationalYTDPage', () => {
  it('renderiza secciones críticas con MSW activado', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Vista Nacional Year To Date')).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText('NPS nacional actual')).toBeInTheDocument();
      expect(screen.getByText('Distribución NPS')).toBeInTheDocument();
      expect(screen.getByText('Tendencia mensual')).toBeInTheDocument();
      expect(screen.getByText('Principales causas de fricción')).toBeInTheDocument();
      expect(screen.getByText('Fortalezas mencionadas')).toBeInTheDocument();
      expect(screen.getByText('Sucursales críticas')).toBeInTheDocument();
      expect(screen.getByText('Rankings nacionales')).toBeInTheDocument();
      expect(screen.getByText('Acciones sugeridas')).toBeInTheDocument();
      expect(screen.getByText('Voz de los pasivos')).toBeInTheDocument();
      expect(screen.getByText('Insights generados')).toBeInTheDocument();
    });
    expect(screen.getByText(/Objetivos NPS sintéticos/)).toBeInTheDocument();
  });
});
