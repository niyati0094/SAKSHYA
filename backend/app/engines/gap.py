"""Deterministic gap detection and recommendation ranking.

Pure functions over competency results. No language model participates in
deciding what a learner should do next: severity is arithmetic over the level
shortfall, evidence sufficiency and role criticality, and ranking is a sort on
that severity. The "why" strings are assembled from the same components that
produced the number, so an explanation cannot describe a different calculation
from the one that ran.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.competency import CompetencyResult, CompetencyStatus

# --------------------------------------------------------------------------
# Expert-defined weights (auditable in one place, like engines/constants.py)
# --------------------------------------------------------------------------

#: How much a role depends on the competency. Multiplies the severity.
CRITICALITY_MULTIPLIER: dict[str, float] = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
}

#: Contribution weights for the three severity components (sum to 1.0).
SEVERITY_WEIGHTS: dict[str, float] = {
    "level_shortfall": 0.5,   # how far below target
    "evidence_deficit": 0.3,  # how little we actually know
    "criticality": 0.2,       # how much the role depends on it
}

#: Highest level on the scale, used to normalise the shortfall.
MAX_LEVEL = 4

SEVERITY_BANDS: list[tuple[float, str]] = [
    (0.60, "urgent"),
    (0.35, "significant"),
    (0.15, "moderate"),
    (0.0, "minor"),
]

#: Below this confidence, a gap is treated as unverified rather than measured.
UNVERIFIED_CONFIDENCE = 0.5


@dataclass(frozen=True)
class Gap:
    competency_id: int
    competency_code: str
    competency_name: str
    current_level: int
    target_level: int
    level_shortfall: int
    status: str
    confidence: float
    criticality: str
    severity: float
    severity_band: str
    #: True when the shortfall is driven by not knowing, not by low mastery.
    evidence_limited: bool
    reasons: list[str] = field(default_factory=list)


def severity_band(severity: float) -> str:
    for threshold, label in SEVERITY_BANDS:
        if severity >= threshold:
            return label
    return SEVERITY_BANDS[-1][1]


def calculate_gap(
    *,
    competency_id: int,
    competency_code: str,
    competency_name: str,
    target_level: int,
    criticality: str,
    result: CompetencyResult,
) -> Gap | None:
    """Compute the gap for one competency, or None when the target is met.

    A competency with no usable evidence is treated as a *full* shortfall
    rather than as zero gap: not knowing whether someone can do something is a
    training need, not a pass.
    """
    unproven = result.status in {
        CompetencyStatus.NO_EVIDENCE,
        CompetencyStatus.INSUFFICIENT_EVIDENCE,
    }
    current_level = 0 if unproven else result.level

    if not unproven and current_level >= target_level:
        return None

    shortfall = max(0, target_level - current_level)

    # Component 1: distance below target, normalised by the scale.
    level_shortfall = shortfall / MAX_LEVEL

    # Component 2: how much of the picture is missing. Low confidence means the
    # estimate itself is unreliable, which is its own reason to intervene.
    evidence_deficit = 1.0 - min(1.0, result.confidence)

    # Component 3: how much the role depends on this competency.
    criticality_score = CRITICALITY_MULTIPLIER.get(criticality, 0.5)

    severity = (
        level_shortfall * SEVERITY_WEIGHTS["level_shortfall"]
        + evidence_deficit * SEVERITY_WEIGHTS["evidence_deficit"]
        + criticality_score * SEVERITY_WEIGHTS["criticality"]
    )
    # Criticality scales the whole gap, not just its own term: a shortfall in a
    # non-critical competency is genuinely less urgent than the same shortfall
    # in a critical one.
    severity = round(severity * (0.55 + 0.45 * criticality_score), 4)

    return Gap(
        competency_id=competency_id,
        competency_code=competency_code,
        competency_name=competency_name,
        current_level=current_level,
        target_level=target_level,
        level_shortfall=shortfall,
        status=result.status,
        confidence=result.confidence,
        criticality=criticality,
        severity=severity,
        severity_band=severity_band(severity),
        evidence_limited=unproven or result.confidence < UNVERIFIED_CONFIDENCE,
        reasons=_reasons(
            result=result,
            target_level=target_level,
            current_level=current_level,
            shortfall=shortfall,
            criticality=criticality,
            unproven=unproven,
        ),
    )


def _reasons(
    *,
    result: CompetencyResult,
    target_level: int,
    current_level: int,
    shortfall: int,
    criticality: str,
    unproven: bool,
) -> list[str]:
    reasons: list[str] = []

    if unproven:
        if result.status == CompetencyStatus.NO_EVIDENCE:
            reasons.append(
                f"No accepted evidence exists, so this competency is unproven "
                f"against a required level {target_level}."
            )
        else:
            reasons.append(
                f"Evidence is too thin to assert a level (effective weight "
                f"{result.effective_evidence:.2f}), so the required level "
                f"{target_level} is unproven."
            )
    else:
        reasons.append(
            f"Current level {current_level} is {shortfall} below the required "
            f"level {target_level}."
        )

    if result.confidence < UNVERIFIED_CONFIDENCE:
        breakdown = result.confidence_breakdown
        limiting = breakdown.limiting_factor if breakdown else "evidence volume"
        reasons.append(
            f"Confidence is low ({result.confidence:.2f}), limited by {limiting}."
        )

    if criticality == "critical":
        reasons.append("This competency is critical for the assigned role.")
    elif criticality == "high":
        reasons.append("This competency is of high importance for the assigned role.")

    return reasons


def rank_gaps(gaps: list[Gap]) -> list[Gap]:
    """Most severe first. Ties broken deterministically by code, never randomly."""
    return sorted(gaps, key=lambda gap: (-gap.severity, gap.competency_code))
