"""Deterministic recommendation engine.

Recommendations are ranked by gap severity and sequenced Learn -> Practice ->
Prove. No language model participates in selecting or ordering them: the
ranking is a sort on the deterministic gap severity, and the stage is chosen by
rule from the learner's current evidence.

Each recommendation carries the reasons that produced it, assembled from the
same values used in the calculation - so "why was this recommended?" is
answered by the calculation itself rather than by a generated narrative.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.catalog.base import LearningResource, ResourceKind
from app.engines.competency import CompetencyResult, CompetencyStatus
from app.engines.gap import Gap

#: Evidence types that count as having practised, as opposed to having read.
PRACTICE_EVIDENCE_TYPES = frozenset({"simulation", "practical_submission", "sme_verified"})


@dataclass(frozen=True)
class Recommendation:
    competency_code: str
    competency_name: str
    stage: str
    resource: LearningResource
    severity: float
    severity_band: str
    rank: int
    reasons: list[str] = field(default_factory=list)
    #: Prerequisite competencies not yet established, if any.
    unmet_prerequisites: list[str] = field(default_factory=list)
    blocked: bool = False


def choose_stage(result: CompetencyResult, evidence_types: set[str]) -> str:
    """Pick the next stage in Learn -> Practice -> Prove.

    The rule is about what kind of evidence exists, not about scores:

    * nothing accepted at all -> LEARN
    * only passive evidence   -> PRACTICE
    * already practised       -> PROVE
    """
    if result.status == CompetencyStatus.NO_EVIDENCE or not evidence_types:
        return ResourceKind.LEARN

    if not (evidence_types & PRACTICE_EVIDENCE_TYPES):
        # Read a course or answered a quiz, but never done the work.
        return ResourceKind.PRACTICE

    # Already practised, yet still short of the role's target: the remaining
    # step is to demonstrate the capability and generate stronger evidence.
    return ResourceKind.PROVE


def stage_reason(stage: str, result: CompetencyResult, evidence_types: set[str]) -> str:
    if stage == ResourceKind.LEARN:
        return "No accepted evidence yet, so the pathway starts with learning."
    if stage == ResourceKind.PRACTICE:
        kinds = ", ".join(sorted(evidence_types)) or "none"
        return (
            f"Existing evidence is passive ({kinds}); practice is needed before "
            "capability can be demonstrated."
        )
    return (
        "Practice has been recorded, so the next step is to demonstrate the "
        "capability and generate stronger evidence."
    )


def build_recommendations(
    *,
    gaps: list[Gap],
    results_by_code: dict[str, CompetencyResult],
    evidence_types_by_code: dict[str, set[str]],
    established_codes: set[str],
    resources_for: dict[str, list[LearningResource]],
    limit: int = 5,
) -> list[Recommendation]:
    """Rank interventions across all gaps, most severe first.

    `gaps` must already be ranked by the gap engine. Ties were broken there
    deterministically, so this function preserves that order rather than
    re-sorting.
    """
    recommendations: list[Recommendation] = []

    for gap in gaps:
        if len(recommendations) >= limit:
            break

        result = results_by_code.get(gap.competency_code)
        if result is None:
            continue

        evidence_types = evidence_types_by_code.get(gap.competency_code, set())
        stage = choose_stage(result, evidence_types)

        resource = _pick_resource(
            resources_for.get(gap.competency_code, []), stage, gap.target_level
        )
        if resource is None:
            continue

        unmet = [
            code
            for code in resource.prerequisites
            if code != gap.competency_code and code not in established_codes
        ]

        reasons = [
            *gap.reasons,
            stage_reason(stage, result, evidence_types),
        ]
        if unmet:
            reasons.append(
                "Prerequisite not yet established: " + ", ".join(unmet) + "."
            )
        else:
            reasons.append("Required prerequisites are satisfied.")

        recommendations.append(
            Recommendation(
                competency_code=gap.competency_code,
                competency_name=gap.competency_name,
                stage=stage,
                resource=resource,
                severity=gap.severity,
                severity_band=gap.severity_band,
                rank=len(recommendations) + 1,
                reasons=reasons,
                unmet_prerequisites=unmet,
                blocked=bool(unmet),
            )
        )

    return recommendations


def _pick_resource(
    resources: list[LearningResource], stage: str, target_level: int
) -> LearningResource | None:
    """Closest resource at the required stage, preferring the target level.

    Falls back through the progression rather than returning nothing: if a
    competency has no PROVE resource, a PRACTICE one is still useful.
    """
    fallbacks = {
        ResourceKind.PROVE: [ResourceKind.PROVE, ResourceKind.PRACTICE, ResourceKind.LEARN],
        ResourceKind.PRACTICE: [ResourceKind.PRACTICE, ResourceKind.LEARN, ResourceKind.PROVE],
        ResourceKind.LEARN: [ResourceKind.LEARN, ResourceKind.PRACTICE, ResourceKind.PROVE],
    }

    def best_of(items: list[LearningResource]) -> LearningResource:
        # Closest pitch to the required level; ties broken by id so the choice
        # is reproducible.
        return min(
            items,
            key=lambda item: (abs(item.target_level - target_level), item.external_id),
        )

    # A resource the learner can actually complete beats one they can only read
    # about. Without this, a learner whose next step is "practise" is pointed at
    # a catalogue entry that leads nowhere, while a runnable simulation for the
    # same competency sits one stage away.
    #
    # LEARN is exempt: a learner with no evidence at all should be sent to the
    # learning material even when it is not clickable here. Jumping them
    # straight to a scored simulation because it happens to be interactive
    # would skip the stage they actually need.
    prefer_interactive = stage != ResourceKind.LEARN
    first_non_interactive: LearningResource | None = None

    for candidate_stage in fallbacks.get(stage, [stage]):
        matching = [item for item in resources if item.kind == candidate_stage]
        if not matching:
            continue

        if prefer_interactive:
            interactive = [item for item in matching if item.is_interactive]
            if interactive:
                return best_of(interactive)

            if first_non_interactive is None:
                first_non_interactive = best_of(matching)
        else:
            return best_of(matching)

    return first_non_interactive
