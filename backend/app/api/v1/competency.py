"""Competency profile, evidence ledger, and the explainability endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.engines import constants
from app.engines.competency import level_label
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.competency import (
    CompetencyDetailOut,
    CompetencyOut,
    CompetencyProfileOut,
    EvidenceOut,
    StatisticalRoleOut,
)
from app.services import competency_service as service

router = APIRouter(tags=["competency"])

PROTOTYPE_NOTICE = (
    "Prototype sample data. Role-to-competency mappings shown here are "
    "illustrative and are not official Government of India competency mappings."
)


def _evidence_out(evidence: Evidence) -> EvidenceOut:
    return EvidenceOut(
        id=evidence.id,
        competency_id=evidence.competency_id,
        competency_name=evidence.competency.name,
        evidence_type=evidence.evidence_type.value,
        activity_title=evidence.activity_title,
        source=evidence.source,
        raw_score=evidence.raw_score,
        max_score=evidence.max_score,
        normalized_score=round(evidence.normalized_score, 4),
        review_status=evidence.review_status.value,
        reviewed_by=evidence.reviewed_by,
        notes=evidence.notes,
        observed_at=evidence.observed_at,
        is_prototype_data=evidence.is_prototype_data,
    )


@router.get("/me/competency-profile", response_model=CompetencyProfileOut)
def my_competency_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompetencyProfileOut:
    """The learner's competency picture, recomputed from evidence on every call.

    Nothing here is a stored score: each level is derived from the evidence
    ledger by the deterministic engine at request time.
    """
    now = datetime.now(timezone.utc)
    profile = service.build_competency_profile(db, current_user.id, as_of=now)

    return CompetencyProfileOut(
        role=(
            StatisticalRoleOut.model_validate(profile["role"]) if profile["role"] else None
        ),
        summary=profile["summary"],
        competencies=[
            {
                "competency": CompetencyOut.model_validate(entry["competency"]),
                "target_level": entry["target_level"],
                "target_level_label": level_label(entry["target_level"]),
                "criticality": entry["criticality"],
                "meets_target": entry["meets_target"],
                "result": entry["result"],
            }
            for entry in profile["competencies"]
        ],
        calculated_at=now,
        prototype_notice=PROTOTYPE_NOTICE,
    )


@router.get("/me/competencies/{competency_id}", response_model=CompetencyDetailOut)
def my_competency_detail(
    competency_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompetencyDetailOut:
    """Full audit trail for one competency.

    Returns the result, every evidence item, each item's exact contribution to
    the estimate, and the constants used - so the number can be recomputed by
    hand from this response alone.
    """
    competency = service.get_competency(db, competency_id)
    if competency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Competency not found"
        )

    now = datetime.now(timezone.utc)
    result, evidence = service.calculate_for_competency(
        db, current_user.id, competency_id, as_of=now
    )

    target_level: int | None = None
    criticality: str | None = None
    meets_target: bool | None = None

    profile = service.get_profile(db, current_user.id)
    if profile is not None:
        link = service.get_role_link(db, profile.statistical_role_id, competency_id)
        if link is not None:
            target_level = link.target_level
            criticality = link.criticality.value
            meets_target = result.level >= link.target_level

    return CompetencyDetailOut(
        competency=CompetencyOut.model_validate(competency),
        target_level=target_level,
        target_level_label=level_label(target_level) if target_level is not None else None,
        criticality=criticality,
        meets_target=meets_target,
        result=result,
        contributions=result.contributions,
        evidence=[_evidence_out(item) for item in evidence],
        method=method_reference(),
        calculated_at=now,
    )


@router.get("/me/evidence", response_model=list[EvidenceOut])
def my_evidence_ledger(
    competency_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvidenceOut]:
    """Every evidence record for the current user, newest first."""
    evidence = service.get_evidence(db, current_user.id, competency_id)
    return [_evidence_out(item) for item in evidence]


@router.get("/competencies", response_model=list[CompetencyOut])
def list_competencies(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CompetencyOut]:
    return [CompetencyOut.model_validate(item) for item in service.list_competencies(db)]


@router.get("/roles", response_model=list[StatisticalRoleOut])
def list_roles(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StatisticalRoleOut]:
    return [StatisticalRoleOut.model_validate(item) for item in service.list_roles(db)]


@router.get("/competency-method")
def method_reference() -> dict:
    """The scoring rules themselves, served as data.

    Published so the calculation is inspectable rather than taken on trust: a
    reviewer can verify any competency result against these constants.
    """
    return {
        "summary": (
            "Mastery is the recency-weighted, type-weighted mean of accepted "
            "evidence scores. Confidence is a separate weighted combination of "
            "evidence volume, diversity, recency and agreement. No language "
            "model participates in either calculation."
        ),
        "evidence_type_weights": constants.EVIDENCE_TYPE_WEIGHTS,
        "weighting_rationale": (
            "Course completion carries the lowest weight because attendance is "
            "not demonstrated capability. Simulations and expert-reviewed "
            "submissions carry the most."
        ),
        "recency": {
            "half_life_days": constants.RECENCY_HALF_LIFE_DAYS,
            "floor": constants.RECENCY_FLOOR,
        },
        "confidence_weights": constants.CONFIDENCE_WEIGHTS,
        "confidence_targets": {
            "effective_evidence": constants.CONFIDENCE_TARGET_EFFECTIVE_EVIDENCE,
            "distinct_evidence_types": constants.CONFIDENCE_TARGET_TYPE_COUNT,
            "max_dispersion": constants.CONFIDENCE_MAX_DISPERSION,
        },
        "sufficiency_thresholds": {
            "min_effective_evidence": constants.MIN_EFFECTIVE_EVIDENCE,
            "min_confidence": constants.MIN_CONFIDENCE,
        },
        "level_bands": constants.LEVEL_BANDS,
        "level_labels": constants.LEVEL_LABELS,
        "counted_review_statuses": sorted(constants.COUNTED_REVIEW_STATUSES),
    }
