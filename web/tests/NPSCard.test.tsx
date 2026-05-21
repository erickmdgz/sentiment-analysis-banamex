import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NPSCard } from '@/components/NPSCard';

describe('NPSCard', () => {
  it('aplica tono verde cuando gap >= 0', () => {
    const { container } = render(<NPSCard title="NPS" value={70} target={65} gap={5} />);
    const badge = screen.getByLabelText('Brecha 5');
    expect(badge.className).toMatch(/emerald/);
    expect(container.querySelector('.bg-banamex-green')).not.toBeNull();
  });

  it('aplica tono ámbar cuando -10 < gap < 0', () => {
    const { container } = render(<NPSCard title="NPS" value={60} target={65} gap={-5} />);
    const badge = screen.getByLabelText('Brecha -5');
    expect(badge.className).toMatch(/amber/);
    expect(container.querySelector('.bg-banamex-amber')).not.toBeNull();
  });

  it('aplica tono rojo cuando gap <= -10', () => {
    const { container } = render(<NPSCard title="NPS" value={50} target={65} gap={-15} />);
    const badge = screen.getByLabelText('Brecha -15');
    expect(badge.className).toMatch(/rose/);
    expect(container.querySelector('.bg-banamex-red')).not.toBeNull();
  });
});
