import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CausesPanel } from '@/components/CausesPanel';
import type { CauseBucket } from '@/api/schema';

describe('CausesPanel', () => {
  it('ordena los items descendente por count aunque entren desordenados', () => {
    const items: CauseBucket[] = [
      { bucket: 'Bajo', count: 5, pct_of_group: 5, sample_l2: [] },
      { bucket: 'Alto', count: 100, pct_of_group: 50, sample_l2: [] },
      { bucket: 'Medio', count: 30, pct_of_group: 20, sample_l2: [] },
    ];
    render(<CausesPanel title="Test" items={items} />);
    const names = screen.getAllByText(/Alto|Medio|Bajo/).map((el) => el.textContent);
    expect(names[0]).toBe('Alto');
    expect(names[1]).toBe('Medio');
    expect(names[2]).toBe('Bajo');
  });
});
