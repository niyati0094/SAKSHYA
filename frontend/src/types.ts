export type Role = 'learner' | 'sme' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  designation: string | null;
  organization: string | null;
  is_prototype_data: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
}

export interface DashboardPayload {
  user: User;
  capabilities: string[];
  pending_modules: string[];
  prototype_notice: string;
}

export interface HealthPayload {
  status: string;
  app: string;
  environment: string;
  database: string;
}

// ---------------------------------------------------------------------------
// Competency (Milestone 2)
// ---------------------------------------------------------------------------

export type CompetencyStatus = 'established' | 'insufficient_evidence' | 'no_evidence';

export interface Competency {
  id: number;
  code: string;
  name: string;
  description: string | null;
  domain: string | null;
}

export interface StatisticalRole {
  id: number;
  code: string;
  name: string;
  description: string | null;
  is_prototype_data: boolean;
}

export interface ConfidenceBreakdown {
  volume: number;
  diversity: number;
  recency: number;
  agreement: number;
  confidence: number;
  limiting_factor: string;
}

export interface CompetencyResult {
  competency_id: number;
  status: CompetencyStatus;
  mastery: number | null;
  level: number;
  level_label: string;
  confidence: number;
  confidence_breakdown: ConfidenceBreakdown | null;
  evidence_count: number;
  counted_evidence_count: number;
  effective_evidence: number;
  explanation: string[];
}

export interface CompetencyProfileEntry {
  competency: Competency;
  target_level: number;
  target_level_label: string;
  criticality: 'critical' | 'high' | 'medium';
  meets_target: boolean;
  result: CompetencyResult;
}

export interface ProfileSummary {
  total_competencies: number;
  meeting_target: number;
  below_target: number;
  insufficient_evidence: number;
  total_counted_evidence: number;
}

export interface CompetencyProfile {
  role: StatisticalRole | null;
  summary: ProfileSummary;
  competencies: CompetencyProfileEntry[];
  calculated_at: string;
  prototype_notice: string;
}

export interface EvidenceContribution {
  evidence_id: number;
  evidence_type: string;
  score: number;
  type_weight: number;
  recency_factor: number;
  effective_weight: number;
  contribution_share: number;
  counted: boolean;
  excluded_reason: string | null;
}

export interface EvidenceRecord {
  id: number;
  competency_id: number;
  competency_name: string;
  evidence_type: string;
  activity_title: string;
  source: string | null;
  raw_score: number;
  max_score: number;
  normalized_score: number;
  review_status: 'pending' | 'accepted' | 'rejected';
  reviewed_by: string | null;
  notes: string | null;
  observed_at: string;
  is_prototype_data: boolean;
}

export interface CompetencyDetail {
  competency: Competency;
  target_level: number | null;
  target_level_label: string | null;
  criticality: string | null;
  meets_target: boolean | null;
  result: CompetencyResult;
  contributions: EvidenceContribution[];
  evidence: EvidenceRecord[];
  method: {
    summary: string;
    evidence_type_weights: Record<string, number>;
    weighting_rationale: string;
    recency: { half_life_days: number; floor: number };
    confidence_weights: Record<string, number>;
    sufficiency_thresholds: { min_effective_evidence: number; min_confidence: number };
    level_labels: Record<string, string>;
  };
  calculated_at: string;
}
