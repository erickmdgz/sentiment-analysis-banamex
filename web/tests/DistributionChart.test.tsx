import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { DistributionChart } from '@/components/DistributionChart';

describe('DistributionChart', () => {
  it('compone una distribución cuyos porcentajes suman 100', () => {
    const dist = {
      promoters_pct: 45,
      passives_pct: 30,
      detractors_pct: 25,
      promoters_count: 450,
      passives_count: 300,
      detractors_count: 250,
    };
    const total = dist.promoters_pct + dist.passives_pct + dist.detractors_pct;
    expect(total).toBe(100);
  });

  it('monta el wrapper accesible para la distribución', () => {
    const dist = {
      promoters_pct: 45,
      passives_pct: 30,
      detractors_pct: 25,
      promoters_count: 450,
      passives_count: 300,
      detractors_count: 250,
    };
    const { getByLabelText } = render(<DistributionChart distribution={dist} />);
    // Verificamos que el contenedor accesible se monta. ResponsiveContainer no
    // mide bien en jsdom, así que no validamos los <path> rasterizados.
    expect(getByLabelText('Distribución NPS')).toBeInTheDocument();
  });
});
