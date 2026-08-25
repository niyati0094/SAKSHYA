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

// ---------------------------------------------------------------------------
// Documents and generated questions (Milestone 3)
// ---------------------------------------------------------------------------

export interface DocumentSummary {
  id: number;
  title: string;
  filename: string;
  content_type: string;
  byte_size: number;
  page_count: number;
  chunk_count: number;
  status: 'uploaded' | 'processing' | 'ready' | 'failed';
  error_message: string | null;
  uploaded_at: string;
  is_prototype_data: boolean;
}

export interface Citation {
  document_id: number;
  document_title: string;
  chunk_id: number;
  page_number: number | null;
  section_title: string | null;
  quote: string;
}

export interface GeneratedQuestion {
  id: number;
  stem: string;
  options: string[];
  correct_index: number;
  explanation: string;
  citation: Citation;
  grounding_status: 'grounded' | 'ungrounded';
  grounding_score: number;
  grounding_note: string | null;
  competency_id: number | null;
  competency_name: string | null;
  competency_tag_score: number | null;
  review_status: 'pending' | 'approved' | 'rejected';
  review_note: string | null;
  reviewed_at: string | null;
  edited: boolean;
  generator: string;
  generation_strategy: string | null;
  is_prototype_data: boolean;
}

export interface ReviewSummary {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  ungrounded: number;
  untagged: number;
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

// ---------------------------------------------------------------------------
// Simulation lab (Milestone 4)
// ---------------------------------------------------------------------------

export interface ScenarioSummary {
  code: string;
  title: string;
  summary: string;
  competency_code: string;
  estimated_minutes: number;
  decision_count: number;
}

export interface ScenarioOption {
  key: string;
  text: string;
}

export interface ScenarioDecision {
  key: string;
  prompt: string;
  context: string;
  options: ScenarioOption[];
}

export interface ScenarioDetail extends ScenarioSummary {
  briefing: string;
  decisions: ScenarioDecision[];
  prototype_notice: string;
}

export interface DecisionOutcome {
  decision_key: string;
  prompt: string;
  chosen_key: string | null;
  chosen_text: string | null;
  credit: number;
  weight: number;
  rationale: string;
  best_key: string;
  best_text: string;
  is_best: boolean;
  answered: boolean;
}

export interface AttemptResult {
  attempt_id: number;
  scenario_code: string;
  scenario_title: string;
  score: number;
  max_score: number;
  percentage: number;
  band: string;
  answered_count: number;
  total_decisions: number;
  outcomes: DecisionOutcome[];
  explanation: string[];
  debrief: string | null;
  evidence_id: number | null;
  competency_code: string;
  scoring_note: string;
}

export interface SimulationAttemptSummary {
  id: number;
  scenario_code: string;
  scenario_title: string;
  percentage: number;
  band: string;
  completed_at: string;
  evidence_id: number | null;
}

// ---------------------------------------------------------------------------
// Gaps and pathway (Milestone 5)
// ---------------------------------------------------------------------------

export interface Gap {
  competency_id: number;
  competency_code: string;
  competency_name: string;
  current_level: number;
  target_level: number;
  level_shortfall: number;
  status: string;
  confidence: number;
  criticality: string;
  severity: number;
  severity_band: 'urgent' | 'significant' | 'moderate' | 'minor';
  evidence_limited: boolean;
  reasons: string[];
}

export interface LearningResourceOut {
  external_id: string;
  title: string;
  description: string;
  kind: 'learn' | 'practice' | 'prove';
  competency_code: string;
  target_level: number;
  estimated_minutes: number;
  provider: string;
  prerequisites: string[];
  url: string | null;
  is_interactive: boolean;
  is_prototype_data: boolean;
}

export interface Recommendation {
  rank: number;
  competency_code: string;
  competency_name: string;
  stage: 'learn' | 'practice' | 'prove';
  resource: LearningResourceOut;
  severity: number;
  severity_band: 'urgent' | 'significant' | 'moderate' | 'minor';
  reasons: string[];
  unmet_prerequisites: string[];
  blocked: boolean;
}

export interface Pathway {
  role: StatisticalRole | null;
  gaps: Gap[];
  recommendations: Recommendation[];
  catalog: { adapter: string; is_live_integration: boolean; notice: string };
  calculated_at: string;
  method_note: string;
}

// ---------------------------------------------------------------------------
// Admin analytics (Milestone 6)
// ---------------------------------------------------------------------------

export interface TrainingNeed {
  competency_code: string;
  competency_name: string;
  criticality: string;
  target_level: number;
  learners_with_gap: number;
  learners_unproven: number;
  average_severity: number;
  share_of_learners: number;
}

export interface OrganisationOverview {
  learner_count: number;
  learners_with_profile: number;
  total_gaps: number;
  urgent_gaps: number;
  role_distribution: { role_name: string; learner_count: number }[];
  training_needs: TrainingNeed[];
  calculated_at: string;
  notice: string;
}
