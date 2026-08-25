"""Deterministic competency engine.

This module answers the question SAKSHYA exists to answer:

    "Why does the system believe I have this competency level?"

It is a pure function of the evidence supplied to it. Given the same evidence
and the same `as_of` timestamp it always returns the same result. It performs
no I/O, imports nothing from `app.ai`, and no language model participates in
any number it produces. The `explain()` output is assembled from the same
arithmetic that produced the score, so the explanation cannot drift from the
result it describes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from app.engines.constants import (
    CONFIDENCE_MAX_DISPERSION,
    CONFIDENCE_SINGLE_ITEM_AGREEMENT,
    CONFIDENCE_TARGET_EFFECTIVE_EVIDENCE,
    CONFIDENCE_TARGET_TYPE_COUNT,
    CONFIDENCE_WEIGHTS,
    COUNTED_REVIEW_STATUSES,
    DEFAULT_EVIDENCE_WEIGHT,
    EVIDENCE_TYPE_WEIGHTS,
    LEVEL_BANDS,
    LEVEL_LABELS,
    MIN_CONFIDENCE,
    MIN_EFFECTIVE_EVIDENCE,
    RECENCY_FLOOR,
    RECENCY_HALF_LIFE_DAYS,
)


class CompetencyStatus:
    """Outcome categories. INSUFFICIENT_EVIDENCE is a real answer, not a failure."""

    NO_EVIDENCE = "no_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ESTABLISHED = "established"


# ---------------------------------------------------------------------------
# Inputs and outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceInput:
    """One piece of evidence, normalised for the engine.

    `score` is always 0..1 - callers normalise raw marks before calling in, so
    the engine never has to know about differing maximum scores.
    """

    evidence_id: int
    evidence_type: str
    score: float
    observed_at: datetime
    review_status: str = "accepted"
    weight_override: float | None = None


@dataclass(frozen=True)
class EvidenceContribution:
    """Exactly how one evidence item moved the mastery estimate."""

    evidence_id: int
    evidence_type: str
    score: float
    type_weight: float
    recency_factor: float
    effective_weight: float
    #: Share of the final mastery estimate attributable to this item (0..1).
    contribution_share: float
    counted: bool
    excluded_reason: str | None = None


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """The four components behind the confidence figure, each 0..1."""

    volume: float
    diversity: float
    recency: float
    agreement: float
    confidence: float

    #: Name of the component holding confidence back the most.
    limiting_factor: str


@dataclass(frozen=True)
class CompetencyResult:
    competency_id: int
    status: str
    mastery: float | None
    level: int
    level_label: str
    confidence: float
    confidence_breakdown: ConfidenceBreakdown | None
    evidence_count: int
    counted_evidence_count: int
    effective_evidence: float
    contributions: list[EvidenceContribution] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Component calculations
# ---------------------------------------------------------------------------


def type_weight_for(evidence_type: str) -> float:
    """Expert-defined weight for an evidence type.

    Course completion is weighted lowest by design: attendance is not
    demonstrated capability.
    """
    return EVIDENCE_TYPE_WEIGHTS.get(evidence_type, DEFAULT_EVIDENCE_WEIGHT)


def recency_factor(observed_at: datetime, as_of: datetime) -> float:
    """Exponential decay with a half-life, floored so old evidence still counts."""
    age_days = (as_of - observed_at).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    decayed = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return max(RECENCY_FLOOR, decayed)


def _population_stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _agreement(scores: list[float]) -> float:
    """How consistent the evidence is with itself.

    One item cannot disagree with anything, so it yields a neutral value rather
    than a misleading perfect score.
    """
    if len(scores) < 2:
        return CONFIDENCE_SINGLE_ITEM_AGREEMENT
    dispersion = _population_stdev(scores)
    return max(0.0, 1.0 - min(1.0, dispersion / CONFIDENCE_MAX_DISPERSION))


def level_for_mastery(mastery: float) -> int:
    """Translate continuous mastery into a discrete competency level."""
    level = 0
    for candidate in sorted(LEVEL_BANDS):
        if mastery >= LEVEL_BANDS[candidate]:
            level = candidate
    return level


def level_label(level: int) -> str:
    return LEVEL_LABELS.get(level, "Unknown")


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------


def calculate_competency(
    competency_id: int,
    evidence: list[EvidenceInput],
    as_of: datetime,
) -> CompetencyResult:
    """Compute mastery, confidence and status from an evidence list.

    Deterministic and reproducible: identical inputs always yield identical
    output. `as_of` is an explicit parameter rather than a call to `now()` so
    results are reproducible and testable.
    """
    contributions: list[EvidenceContribution] = []
    counted: list[tuple[EvidenceInput, float, float]] = []  # (item, type_weight, recency)

    for item in evidence:
        weight = (
            item.weight_override
            if item.weight_override is not None
            else type_weight_for(item.evidence_type)
        )
        recency = recency_factor(item.observed_at, as_of)
        is_counted = item.review_status in COUNTED_REVIEW_STATUSES

        if is_counted:
            counted.append((item, weight, recency))
            reason = None
        else:
            reason = f"review status is '{item.review_status}', not accepted"

        contributions.append(
            EvidenceContribution(
                evidence_id=item.evidence_id,
                evidence_type=item.evidence_type,
                score=item.score,
                type_weight=weight,
                recency_factor=round(recency, 4),
                effective_weight=round(weight * recency, 4) if is_counted else 0.0,
                contribution_share=0.0,  # filled in below once the total is known
                counted=is_counted,
                excluded_reason=reason,
            )
        )

    if not counted:
        return CompetencyResult(
            competency_id=competency_id,
            status=CompetencyStatus.NO_EVIDENCE,
            mastery=None,
            level=0,
            level_label=level_label(0),
            confidence=0.0,
            confidence_breakdown=None,
            evidence_count=len(evidence),
            counted_evidence_count=0,
            effective_evidence=0.0,
            contributions=contributions,
            explanation=_explain_no_evidence(evidence),
        )

    # --- Mastery: recency-weighted, type-weighted mean of evidence scores ---
    effective_weights = [weight * recency for _, weight, recency in counted]
    total_effective = sum(effective_weights)

    if total_effective == 0.0:
        # Every accepted item carries zero weight - in practice, nothing but
        # course completions. There is genuinely no evidence of capability
        # here, only evidence of attendance, so no mastery is computed at all.
        return CompetencyResult(
            competency_id=competency_id,
            status=CompetencyStatus.NO_EVIDENCE,
            mastery=None,
            level=0,
            level_label=level_label(0),
            confidence=0.0,
            confidence_breakdown=None,
            evidence_count=len(evidence),
            counted_evidence_count=len(counted),
            effective_evidence=0.0,
            contributions=contributions,
            explanation=_explain_zero_weight(counted),
        )
    mastery = (
        sum(
            item.score * effective
            for (item, _, _), effective in zip(counted, effective_weights, strict=True)
        )
        / total_effective
    )

    # Attribute each item's share of the estimate, so the ledger can show
    # precisely which evidence drove the result.
    share_by_id = {
        item.evidence_id: effective / total_effective
        for (item, _, _), effective in zip(counted, effective_weights, strict=True)
    }
    contributions = [
        EvidenceContribution(
            **{
                **contribution.__dict__,
                "contribution_share": round(share_by_id.get(contribution.evidence_id, 0.0), 4),
            }
        )
        for contribution in contributions
    ]

    # --- Confidence: four independent components ---
    scores = [item.score for item, _, _ in counted]
    distinct_types = {item.evidence_type for item, _, _ in counted}

    volume = min(1.0, total_effective / CONFIDENCE_TARGET_EFFECTIVE_EVIDENCE)
    diversity = min(1.0, len(distinct_types) / CONFIDENCE_TARGET_TYPE_COUNT)
    recency = max(recency for _, _, recency in counted)
    agreement = _agreement(scores)

    components = {
        "volume": volume,
        "diversity": diversity,
        "recency": recency,
        "agreement": agreement,
    }
    confidence = sum(value * CONFIDENCE_WEIGHTS[name] for name, value in components.items())
    confidence = max(0.0, min(1.0, confidence))

    # The limiting factor is the component losing the most weighted confidence -
    # i.e. where improvement would help most.
    limiting_factor = max(
        components,
        key=lambda name: (1.0 - components[name]) * CONFIDENCE_WEIGHTS[name],
    )

    breakdown = ConfidenceBreakdown(
        volume=round(volume, 4),
        diversity=round(diversity, 4),
        recency=round(recency, 4),
        agreement=round(agreement, 4),
        confidence=round(confidence, 4),
        limiting_factor=limiting_factor,
    )

    # --- Status: refuse to assert a level on thin evidence ---
    insufficient = total_effective < MIN_EFFECTIVE_EVIDENCE or confidence < MIN_CONFIDENCE
    status = (
        CompetencyStatus.INSUFFICIENT_EVIDENCE if insufficient else CompetencyStatus.ESTABLISHED
    )
    level = 0 if insufficient else level_for_mastery(mastery)

    return CompetencyResult(
        competency_id=competency_id,
        status=status,
        mastery=round(mastery, 4),
        level=level,
        level_label=level_label(level),
        confidence=round(confidence, 4),
        confidence_breakdown=breakdown,
        evidence_count=len(evidence),
        counted_evidence_count=len(counted),
        effective_evidence=round(total_effective, 4),
        contributions=contributions,
        explanation=_explain(
            mastery=mastery,
            level=level,
            status=status,
            breakdown=breakdown,
            counted_count=len(counted),
            excluded_count=len(evidence) - len(counted),
            total_effective=total_effective,
            distinct_types=len(distinct_types),
        ),
    )


# ---------------------------------------------------------------------------
# Explanations (deterministic - assembled from the same arithmetic)
# ---------------------------------------------------------------------------

_LIMITING_FACTOR_ADVICE = {
    "volume": "more evidence would raise confidence most",
    "diversity": "a different kind of evidence (e.g. a simulation) would raise confidence most",
    "recency": "more recent evidence would raise confidence most",
    "agreement": "evidence scores disagree with each other, which lowers confidence",
}


def _explain_zero_weight(counted: list[tuple[EvidenceInput, float, float]]) -> list[str]:
    """Explain a competency whose only evidence is weighted zero."""
    types = sorted({item.evidence_type for item, _, _ in counted})
    readable = ", ".join(t.replace("_", " ") for t in types)
    best = max(item.score for item, _, _ in counted)

    return [
        f"{len(counted)} accepted record(s) exist ({readable}), but they carry a "
        f"combined weight of zero, so no mastery is calculated.",
        f"The highest recorded score is {best:.0%}, and it still establishes "
        "nothing: course completion is weighted 0.0 by design, because "
        "attendance is not demonstrated capability.",
        "Complete an assessment or a simulation to generate evidence that counts.",
    ]


def _explain_no_evidence(evidence: list[EvidenceInput]) -> list[str]:
    if not evidence:
        return [
            "No evidence has been recorded for this competency, so no level is asserted.",
            "Complete an assessment or simulation to generate the first evidence.",
        ]
    return [
        f"{len(evidence)} evidence item(s) exist but none are accepted, "
        "so no level is asserted.",
        "Evidence awaiting or failing subject matter expert review does not "
        "contribute to a competency estimate.",
    ]


def _explain(
    *,
    mastery: float,
    level: int,
    status: str,
    breakdown: ConfidenceBreakdown,
    counted_count: int,
    excluded_count: int,
    total_effective: float,
    distinct_types: int,
) -> list[str]:
    lines = [
        f"Mastery {mastery:.2f} is the recency-weighted mean of {counted_count} "
        f"accepted evidence item(s), total effective weight {total_effective:.2f}.",
    ]

    if excluded_count:
        lines.append(
            f"{excluded_count} further evidence item(s) were excluded because they "
            "are not accepted."
        )

    if status == CompetencyStatus.INSUFFICIENT_EVIDENCE:
        reasons = []
        if total_effective < MIN_EFFECTIVE_EVIDENCE:
            reasons.append(
                f"effective evidence {total_effective:.2f} is below the "
                f"{MIN_EFFECTIVE_EVIDENCE:.2f} required"
            )
        if breakdown.confidence < MIN_CONFIDENCE:
            reasons.append(
                f"confidence {breakdown.confidence:.2f} is below the "
                f"{MIN_CONFIDENCE:.2f} required"
            )
        lines.append(
            "No level is asserted because " + " and ".join(reasons) + "."
        )
    else:
        lines.append(f"This places the competency at level {level} ({level_label(level)}).")

    lines.append(
        f"Confidence {breakdown.confidence:.2f} = volume {breakdown.volume:.2f}, "
        f"diversity {breakdown.diversity:.2f} ({distinct_types} evidence type(s)), "
        f"recency {breakdown.recency:.2f}, agreement {breakdown.agreement:.2f}."
    )
    lines.append(
        f"Limiting factor: {breakdown.limiting_factor} - "
        f"{_LIMITING_FACTOR_ADVICE[breakdown.limiting_factor]}."
    )
    return lines
