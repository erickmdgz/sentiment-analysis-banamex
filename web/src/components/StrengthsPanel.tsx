import type { StrengthBucket } from '@/api/schema';
import { CausesPanel } from './CausesPanel';

interface Props {
  title?: string;
  items: StrengthBucket[];
  limit?: number;
  description?: string;
}

export function StrengthsPanel({ title = 'Fortalezas mencionadas', items, limit, description }: Props) {
  return <CausesPanel title={title} items={items} variant="strength" limit={limit} description={description} />;
}
