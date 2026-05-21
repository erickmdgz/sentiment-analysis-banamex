// Tipos compartidos derivados manualmente de los DTOs Pydantic
// declarados en docs/plan_implementacion/01_contratos_compartidos.md §4.
// En Etapa 2 este archivo se reemplaza por `openapi-typescript ../api/openapi.json`.

export type NPSGroup = 'Promotor' | 'Pasivo' | 'Detractor';
export type Polarity = 'pos' | 'neu' | 'neg';
export type Priority = 'alta' | 'media' | 'baja';
export type InsightCategory =
  | 'nps'
  | 'brecha'
  | 'fortaleza'
  | 'fricción'
  | 'personal'
  | 'comparación'
  | 'cobertura';

export interface NPSDistribution {
  promoters_pct: number;
  passives_pct: number;
  detractors_pct: number;
  promoters_count: number;
  passives_count: number;
  detractors_count: number;
}

export interface NPSSummary {
  nps_actual: number;
  nps_target: number | null;
  gap: number | null;
  total_responses: number;
  distribution: NPSDistribution;
}

export interface MonthlyPoint {
  month: string;
  nps: number;
  responses: number;
}

export interface MonthlyTrend {
  points: MonthlyPoint[];
}

export interface CauseBucket {
  bucket: string;
  count: number;
  pct_of_group: number;
  sample_l2: string[];
}

export type StrengthBucket = CauseBucket;

export interface CriticalBranch {
  branch_id: string;
  nps_actual: number;
  nps_target: number | null;
  gap: number | null;
  detractors_pct: number;
  triggered_conditions: string[];
}

export interface RankingItem {
  branch_id: string;
  value: number;
  label: string;
}

export interface Ranking {
  name: string;
  items: RankingItem[];
}

export interface Rankings {
  worst_nps: Ranking;
  worst_gap: Ranking;
  most_detractors: Ranking;
  worsened: Ranking;
  improved: Ranking;
}

export interface SuggestedAction {
  text: string;
  priority: Priority;
  related_bucket: string | null;
  related_branches: string[];
}

export interface ImpactByCategory {
  bucket: string;
  impact_points: number;
}

export interface Insight {
  text: string;
  category: InsightCategory;
}

export interface WordFrequency {
  word: string;
  count: number;
  group?: NPSGroup | null;
}

export interface RepresentativeComment {
  record_id: string;
  verbatim: string;
  nps_rate: number;
  nps_group: NPSGroup;
  response_date: string;
  bucket: string;
}

export interface PersonnelMention {
  name: string;
  polarity: Exclude<Polarity, 'neu'>;
  count: number;
  example_record_id: string;
  example_verbatim: string;
}

export interface NationalYTD {
  nps: NPSSummary;
  trend: MonthlyTrend;
  causes: CauseBucket[];
  strengths: StrengthBucket[];
  critical_branches: CriticalBranch[];
  rankings: Rankings;
  actions: SuggestedAction[];
  impact: ImpactByCategory[];
  insights: Insight[];
  branches_total: number;
  branches_with_target: number;
}

export interface BranchYTD {
  branch_id: string;
  nps: NPSSummary;
  trend: MonthlyTrend;
  causes: CauseBucket[];
  strengths: StrengthBucket[];
  actions: SuggestedAction[];
  insights: Insight[];
  top_words: WordFrequency[];
  representatives: RepresentativeComment[];
  personnel: PersonnelMention[];
}

export interface MonthlyComparison {
  month_a: string;
  month_b: string;
  nps_a: number;
  nps_b: number;
  nps_change: number;
  distribution_a: NPSDistribution;
  distribution_b: NPSDistribution;
  causes_a: CauseBucket[];
  causes_b: CauseBucket[];
  causes_increased: string[];
  causes_decreased: string[];
  strengths_a: StrengthBucket[];
  strengths_b: StrengthBucket[];
  strengths_increased: string[];
  strengths_decreased: string[];
  branches_improved: CriticalBranch[];
  branches_worsened: CriticalBranch[];
  actions: SuggestedAction[];
}

export interface ValidationSummary {
  files_processed: number;
  rows_loaded: number;
  rows_new: number;
  rows_duplicated_ignored: number;
  branches_detected: number;
  period_available: [string, string];
  months_available: string[];
  columns_detected: string[];
  rows_valid: number;
  rows_empty_verbatim: number;
  rows_invalid_nps: number;
  rows_missing_branch: number;
  rows_duplicate_record_id: number;
  rows_invalid_date: number;
}

export interface CoverageSummary {
  branches_detected: number;
  branches_with_target: number;
  branches_without_target: string[];
  branches_with_target_no_responses: string[];
  invalid_targets: string[];
  duplicate_targets: string[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  expires_at: string;
}

export interface AuthMe {
  username: string;
}

export interface UploadResponse {
  file_id: number;
  validation_summary: ValidationSummary;
  already_processed: boolean;
}

export interface UploadStatus {
  file_id: number;
  status: 'parsing' | 'classifying' | 'done' | 'error';
  progress: number;
  error: string | null;
}

export interface BranchListItem {
  branch_id: string;
  response_count: number;
  has_target: boolean;
}

export interface PassiveAnalysis {
  near_promoter: CauseBucket[];
  near_detractor: CauseBucket[];
}

export interface AdminFile {
  id: number;
  filename: string;
  sha256: string;
  rows_inserted: number;
  uploaded_at: string;
}

export interface AnnotationRunRow {
  id: number;
  sample_size: number;
  model: string;
  started_at: string;
  finished_at: string | null;
  runtime_seconds: number | null;
  status: 'running' | 'done' | 'failed';
}

export interface ClassifierRunRow {
  id: number;
  model_path: string;
  trained_on_run_id: number | null;
  trained_at: string;
  n_samples: number;
  n_labels: number;
  f1_micro: number | null;
  f1_macro: number | null;
  hamming_loss: number | null;
}

export interface AdminRuns {
  annotation_runs: AnnotationRunRow[];
  classifier_runs: ClassifierRunRow[];
}

export interface HealthZ {
  status: 'ok';
  db_path: string;
  classifier_loaded: boolean;
}

export interface ErrorResponse {
  detail: string;
  code: string;
  hint?: string;
}
