import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MonthSelector } from '@/components/MonthSelector';

describe('MonthSelector', () => {
  it('pinta opciones a partir de months_available y dispara onChange', () => {
    const onChange = vi.fn();
    render(
      <MonthSelector
        label="Mes"
        value="2026-01"
        onChange={onChange}
        months={['2026-01', '2026-02', '2026-03']}
      />,
    );
    const select = screen.getByLabelText('Mes') as HTMLSelectElement;
    expect(select.options.length).toBe(3);
    expect(select.options[0].textContent).toMatch(/enero 2026/);
    fireEvent.change(select, { target: { value: '2026-02' } });
    expect(onChange).toHaveBeenCalledWith('2026-02');
  });
});
