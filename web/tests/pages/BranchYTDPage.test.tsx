import { describe, expect, it, beforeAll, afterAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { server } from '@/mocks/server';
import { BranchYTDPage } from '@/pages/BranchYTDPage';
import { TOKEN_KEY } from '@/api/client';
import { getBranchYTD, getBranchFacts, makeFakeJWT } from '@/mocks/fixtures';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterAll(() => server.close());
beforeEach(() => {
  server.resetHandlers();
  localStorage.setItem(TOKEN_KEY, makeFakeJWT('demo').token);
});

function renderBranch(branchId: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/branches/${branchId}`]}>
        <Routes>
          <Route path="/branches/:branchId" element={<BranchYTDPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('BranchYTDPage', () => {
  it('muestra banner ámbar cuando la sucursal tiene NPS objetivo', async () => {
    const withTarget = getBranchFacts().find((b) => b.has_target)!;
    renderBranch(withTarget.branch_id);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: new RegExp(withTarget.branch_id) })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText(/Objetivos NPS sintéticos/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/no tiene NPS objetivo configurado/)).toBeNull();
  });

  it('muestra banner azul cuando no hay objetivo', async () => {
    const withoutTarget = getBranchFacts().find((b) => !b.has_target)!;
    renderBranch(withoutTarget.branch_id);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: new RegExp(withoutTarget.branch_id) })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText(/no tiene NPS objetivo configurado/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Objetivos NPS sintéticos/)).toBeNull();
  });

  it('muestra pantalla 404 cuando la sucursal no existe', async () => {
    server.use(
      http.get('/branches/:id/ytd', () =>
        HttpResponse.json({ detail: 'no', code: 'branch_not_found' }, { status: 404 }),
      ),
    );
    renderBranch('XYZ');
    await waitFor(() => {
      expect(screen.getByText('Sucursal no encontrada')).toBeInTheDocument();
    });
  });

  it('getBranchYTD del fixture devuelve datos coherentes', () => {
    const sample = getBranchFacts()[0];
    const ytd = getBranchYTD(sample.branch_id);
    expect(ytd).not.toBeNull();
    expect(ytd!.branch_id).toBe(sample.branch_id);
    expect(ytd!.trend.points.length).toBe(16);
  });
});
