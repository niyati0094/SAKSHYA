"""Competency, evidence and explainability contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompetencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    domain: str | None = None


class StatisticalRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    is_prototype_data: bool


class ConfidenceBreakdownOut(BaseModel):
    # The engine returns frozen dataclasses; allow validation from attributes
    # so engine output can be serialised without a manual mapping layer.
    model_config = ConfigDict(from_attributes=True)

    volume: float
    diversity: float
    recency: float
    agreement: float
    confidence: float
    limiting_factor: str


class EvidenceContributionOut(BaseModel):
    """How a single evidence item moved the estimate."""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: int
    evidence_type: str
    score: float
    type_weight: float
    recency_factor: float
    effective_weight: float
    contribution_share: float
    counted: bool
    excluded_reason: str | None = None


class CompetencyResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competency_id: int
    status: str
    mastery: float | None
    level: int
    level_label: str
    confidence: float
    confidence_breakdown: ConfidenceBreakdownOut | None
    evidence_count: int
    counted_evidence_count: int
    effective_evidence: float
    explanation: list[str]


class CompetencyProfileEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competency: CompetencyOut
    target_level: int
    target_level_label: str
    criticality: str
    meets_target: bool
    result: CompetencyResultOut


class ProfileSummary(BaseModel):
    total_competencies: int
    meeting_target: int
    below_target: int
    insufficient_evidence: int
    total_counted_evidence: int


class CompetencyProfileOut(BaseModel):
    role: StatisticalRoleOut | None
    summary: ProfileSummary
    competencies: list[CompetencyProfileEntry]
    calculated_at: datetime
    prototype_notice: str


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competency_id: int
    competency_name: str
    evidence_type: str
    activity_title: str
    source: str | None
    raw_score: float
    max_score: float
    normalized_score: float
    review_status: str
    reviewed_by: str | None
    notes: str | None
    observed_at: datetime
    is_prototype_data: bool


class CompetencyDetailOut(BaseModel):
    """The full answer to 'why does SAKSHYA believe I have this level?'"""

    competency: CompetencyOut
    target_level: int | None
    target_level_label: str | None
    criticality: str | None
    meets_target: bool | None
    result: CompetencyResultOut
    contributions: list[EvidenceContributionOut]
    evidence: list[EvidenceOut]
    method: dict
    calculated_at: datetime
