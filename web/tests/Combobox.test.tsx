import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Combobox } from '@/components/ui/combobox';

describe('Combobox (BranchSelector core)', () => {
  it('filtra por substring case-insensitive en branch_id', () => {
    const items = Array.from({ length: 100 }, (_, i) => ({
      value: `A-${String(i).padStart(4, '0')}`,
      label: `A-${String(i).padStart(4, '0')}`,
    }));
    const onChange = vi.fn();
    render(<Combobox items={items} value={null} onChange={onChange} />);
    const input = screen.getByLabelText('Buscar sucursal');
    fireEvent.change(input, { target: { value: 'a-0050' } });
    expect(screen.getByText('A-0050')).toBeInTheDocument();
    expect(screen.queryByText('A-0001')).toBeNull();
  });
});
