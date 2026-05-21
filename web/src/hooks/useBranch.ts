import { useParams } from 'react-router-dom';

export function useBranch(): string | null {
  const { branchId } = useParams<{ branchId: string }>();
  return branchId ?? null;
}
