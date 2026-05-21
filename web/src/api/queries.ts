import { useQuery, useMutation, type UseQueryOptions } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  AdminFile,
  AdminRuns,
  AuthMe,
  BranchListItem,
  BranchYTD,
  CauseBucket,
  CoverageSummary,
  CriticalBranch,
  Insight,
  LoginRequest,
  LoginResponse,
  MonthlyComparison,
  MonthlyTrend,
  NationalYTD,
  PassiveAnalysis,
  PersonnelMention,
  Rankings,
  RepresentativeComment,
  StrengthBucket,
  SuggestedAction,
  UploadResponse,
  UploadStatus,
  ValidationSummary,
  WordFrequency,
} from './schema';

const TWO_MINUTES = 2 * 60 * 1000;

// --- Auth ---

export function useLogin() {
  return useMutation<LoginResponse, Error, LoginRequest>({
    mutationFn: (req) => apiClient.post<LoginResponse>('/auth/login', req),
  });
}

export function useMe(enabled = true) {
  return useQuery<AuthMe>({
    queryKey: ['auth', 'me'],
    queryFn: () => apiClient.get<AuthMe>('/auth/me'),
    enabled,
  });
}

// --- Upload + validación ---

export function useUploadFile() {
  return useMutation<UploadResponse, Error, File>({
    mutationFn: (file) => {
      const form = new FormData();
      form.append('file', file);
      return apiClient.postForm<UploadResponse>('/upload', form);
    },
  });
}

export function useUploadStatus(fileId: number | null, options?: { polling?: boolean }) {
  return useQuery<UploadStatus>({
    queryKey: ['upload', fileId, 'status'],
    queryFn: () => apiClient.get<UploadStatus>(`/upload/${fileId}/status`),
    enabled: fileId !== null,
    refetchInterval: (q) => {
      if (!options?.polling) return false;
      const s = q.state.data?.status;
      return s === 'done' || s === 'error' ? false : 2000;
    },
  });
}

export function useValidation(options?: Partial<UseQueryOptions<ValidationSummary>>) {
  return useQuery<ValidationSummary>({
    queryKey: ['validation'],
    queryFn: () => apiClient.get<ValidationSummary>('/validation'),
    ...options,
  });
}

export function useCoverage() {
  return useQuery<CoverageSummary>({
    queryKey: ['validation', 'coverage'],
    queryFn: () => apiClient.get<CoverageSummary>('/validation/coverage'),
  });
}

// --- Nacional ---

export function useNationalYTD() {
  return useQuery<NationalYTD>({
    queryKey: ['national', 'ytd'],
    queryFn: () => apiClient.get<NationalYTD>('/national/ytd'),
  });
}

export function useNationalTrend() {
  return useQuery<MonthlyTrend>({
    queryKey: ['national', 'trend'],
    queryFn: () => apiClient.get<MonthlyTrend>('/national/trend'),
  });
}

export function useNationalCompare(monthA: string | null, monthB: string | null) {
  return useQuery<MonthlyComparison>({
    queryKey: ['national', 'compare', monthA, monthB],
    queryFn: () =>
      apiClient.get<MonthlyComparison>(
        `/national/compare?month_a=${monthA}&month_b=${monthB}`,
      ),
    enabled: Boolean(monthA && monthB),
    staleTime: TWO_MINUTES,
  });
}

export function useCriticalBranches(limit = 10) {
  return useQuery<CriticalBranch[]>({
    queryKey: ['national', 'critical-branches', limit],
    queryFn: () =>
      apiClient.get<CriticalBranch[]>(`/national/critical-branches?limit=${limit}`),
  });
}

export function useNationalRankings() {
  return useQuery<Rankings>({
    queryKey: ['national', 'rankings'],
    queryFn: () => apiClient.get<Rankings>('/national/rankings'),
  });
}

export function useNationalActions(limit = 10) {
  return useQuery<SuggestedAction[]>({
    queryKey: ['national', 'actions', limit],
    queryFn: () => apiClient.get<SuggestedAction[]>(`/national/actions?limit=${limit}`),
  });
}

export function useNationalInsights() {
  return useQuery<Insight[]>({
    queryKey: ['national', 'insights'],
    queryFn: () => apiClient.get<Insight[]>('/national/insights'),
  });
}

export function useNationalPassiveAnalysis() {
  return useQuery<PassiveAnalysis>({
    queryKey: ['national', 'passive-analysis'],
    queryFn: () => apiClient.get<PassiveAnalysis>('/national/passive-analysis'),
  });
}

// --- Sucursales ---

export function useBranchesList(query = '') {
  return useQuery<BranchListItem[]>({
    queryKey: ['branches', 'list', query],
    queryFn: () =>
      apiClient.get<BranchListItem[]>(
        `/branches${query ? `?q=${encodeURIComponent(query)}` : ''}`,
      ),
    staleTime: 10 * 60 * 1000,
  });
}

export function useBranchYTD(branchId: string | null) {
  return useQuery<BranchYTD>({
    queryKey: ['branches', branchId, 'ytd'],
    queryFn: () => apiClient.get<BranchYTD>(`/branches/${branchId}/ytd`),
    enabled: Boolean(branchId),
  });
}

export function useBranchCompare(branchId: string | null, monthA: string | null, monthB: string | null) {
  return useQuery<MonthlyComparison>({
    queryKey: ['branches', branchId, 'compare', monthA, monthB],
    queryFn: () =>
      apiClient.get<MonthlyComparison>(
        `/branches/${branchId}/compare?month_a=${monthA}&month_b=${monthB}`,
      ),
    enabled: Boolean(branchId && monthA && monthB),
  });
}

export function useBranchWords(branchId: string | null, group: string | null, topN = 30) {
  return useQuery<WordFrequency[]>({
    queryKey: ['branches', branchId, 'words', group, topN],
    queryFn: () => {
      const params = new URLSearchParams({ top_n: String(topN) });
      if (group) params.append('group', group);
      return apiClient.get<WordFrequency[]>(
        `/branches/${branchId}/words?${params.toString()}`,
      );
    },
    enabled: Boolean(branchId),
  });
}

export function useBranchRepresentatives(branchId: string | null, nPerTopic = 2) {
  return useQuery<RepresentativeComment[]>({
    queryKey: ['branches', branchId, 'representatives', nPerTopic],
    queryFn: () =>
      apiClient.get<RepresentativeComment[]>(
        `/branches/${branchId}/representatives?n_per_topic=${nPerTopic}`,
      ),
    enabled: Boolean(branchId),
  });
}

export function useBranchPersonnel(branchId: string | null) {
  return useQuery<PersonnelMention[]>({
    queryKey: ['branches', branchId, 'personnel'],
    queryFn: () => apiClient.get<PersonnelMention[]>(`/branches/${branchId}/personnel`),
    enabled: Boolean(branchId),
  });
}

export function useBranchCauses(branchId: string | null) {
  return useQuery<CauseBucket[]>({
    queryKey: ['branches', branchId, 'causes'],
    queryFn: () => apiClient.get<CauseBucket[]>(`/branches/${branchId}/causes`),
    enabled: Boolean(branchId),
  });
}

export function useBranchStrengths(branchId: string | null) {
  return useQuery<StrengthBucket[]>({
    queryKey: ['branches', branchId, 'strengths'],
    queryFn: () => apiClient.get<StrengthBucket[]>(`/branches/${branchId}/strengths`),
    enabled: Boolean(branchId),
  });
}

// --- Admin ---

export function useAdminFiles() {
  return useQuery<AdminFile[]>({
    queryKey: ['admin', 'files'],
    queryFn: () => apiClient.get<AdminFile[]>('/admin/files'),
  });
}

export function useAdminRuns() {
  return useQuery<AdminRuns>({
    queryKey: ['admin', 'runs'],
    queryFn: () => apiClient.get<AdminRuns>('/admin/runs'),
  });
}
