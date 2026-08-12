export type Priority = "high" | "medium" | "low";

export interface MerchantSource {
  id: string;
  kind: string;
  url: string;
  is_verified: boolean;
  created_at: string;
}

export interface MerchantData {
  id: string;
  name: string;
  normalized_name: string;
  branch_name: string | null;
  city: string;
  district: string | null;
  industry: string;
  address: string | null;
  price_range: string | null;
  opening_hours: string | null;
  products: string[];
  strengths: string[];
  sources: MerchantSource[];
  created_at: string;
  updated_at: string;
}

export interface QueryData {
  id: string;
  query_set_id: string;
  text: string;
  category: string;
  reason: string;
  priority: number;
  intent_type?: "recommendation" | "verification";
  fact_keys?: string[];
  review_status: "pending" | "approved" | "rejected";
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type ProfileValue = string | number | boolean | string[];

export interface MerchantProfileFactData {
  id?: string | null;
  field_key: string;
  value: ProfileValue;
  confirmation_status: "pending" | "confirmed" | "rejected";
  confidence?: number | null;
  source_urls: string[];
}

export interface MerchantProfileData {
  merchant_id: string;
  facts: MerchantProfileFactData[];
}

export interface QuerySetData {
  id: string;
  merchant_id: string;
  version: number;
  generator_name: string;
  created_at: string;
  queries: QueryData[];
}

export interface QueryUpdateData {
  text?: string;
  priority?: number;
  review_status?: "pending" | "approved" | "rejected";
  is_enabled?: boolean;
}

export interface CitationData {
  id: string;
  url: string;
  domain: string;
  title: string | null;
  snippet: string | null;
}

export interface QueryResultData {
  id: string;
  query_id: string;
  status: "success" | "failed";
  raw_text: string | null;
  adapter_name: string;
  provider_request_id: string | null;
  attempt_count: number;
  error_message: string | null;
  started_at: string;
  finished_at: string;
  citations: CitationData[];
}

export interface ScanRunData {
  id: string;
  merchant_id: string;
  query_set_id: string;
  adapter_name: string;
  status: "queued" | "running" | "completed" | "partial" | "failed";
  success_count: number;
  failure_count: number;
  error_summary: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  results: QueryResultData[];
}

export interface MetricSnapshotData {
  total_query_count: number;
  valid_query_count: number;
  mention_rate: string | number;
  visibility_stage: "unrecognized" | "relevant" | "mentioned" | "recommended";
  profile_completeness: string | number;
  public_verifiability: string | number;
  high_intent_hit_rate: string | number;
  competitor_gap_closure: string | number;
  readiness_score: string | number;
  task_valid_rate: string | number;
  source_coverage_rate: string | number;
  independent_source_count: number;
  category_coverage: Record<string, string | number>;
  category_mentions: Record<string, number>;
  category_totals: Record<string, number>;
  competitor_counts: Record<string, number>;
  competitor_details: Array<{
    name: string;
    query_count: number;
    categories: string[];
    questions: string[];
    sourceChannels: Array<{
      domain: string;
      citationCount: number;
      access: "maintainable" | "submission" | "reference";
      label: string;
    }>;
    reasons: string[];
    source_count: number;
  }>;
  coverage_gaps: Record<string, string[]>;
  confirmed_target_fields: string[];
}

export interface ReportData {
  merchant_id: string;
  scan_run_id: string;
  metrics: MetricSnapshotData;
  findings: Array<Record<string, unknown>>;
}

export interface HistoryData {
  left: MetricSnapshotData;
  right: MetricSnapshotData;
  deltas: Record<string, string | number>;
}

export interface DashboardData {
  merchant: { id: string; name: string; branchName?: string };
  lastRunAt: string;
  metrics: {
    mentionRate: number;
    visibilityStage: "unrecognized" | "relevant" | "mentioned" | "recommended";
    readinessScore: number;
    profileCompleteness: number;
    publicVerifiability: number;
    highIntentHitRate: number;
    competitorGapClosure: number;
    sourceCoverageRate: number;
    validQueryCount: number;
    totalQueryCount: number;
  };
  trend: Array<{ label: string; target: number }>;
  categories: Array<{ name: string; rate: number; mentioned: number; total: number }>;
  competitors: Array<{
    name: string;
    mentions: number;
    comparisonLevel: "core" | "candidate";
    contexts: string[];
    questions: string[];
    reasons: string[];
    sourceCount: number;
  }>;
  actions: Array<{
    id: string;
    title: string;
    priority: Priority;
    evidenceCount: number;
    description: string;
    steps: string[];
    channels: string[];
    materials: string[];
    example: string;
    completionCriteria: string;
    questions: string[];
    sourceChannels: Array<{
      domain: string;
      citationCount: number;
      access: "maintainable" | "submission" | "reference";
      label: string;
    }>;
  }>;
}
