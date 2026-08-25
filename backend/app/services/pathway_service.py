"""Assembles gaps and the personalised pathway from stored evidence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.catalog import get_catalog
from app.engines.competency import CompetencyResult, CompetencyStatus
from app.engines.gap import Gap, calculate_gap, rank_gaps
from app.engines.recommender import Recommendation, build_recommendations
from app.services import competency_service


def build_pathway(
    db: Session, user_id: int, *, limit: int = 5, as_of: datetime | None = None
) -> dict:
    """Compute gaps and recommendations for a learner.

    Everything is derived at request time from the evidence ledger. No gap or
    recommendation is stored, so they cannot go stale relative to the evidence
    they are supposed to reflect.
    """
    as_of = as_of or datetime.now(timezone.utc)
    profile = competency_service.build_competency_profile(db, user_id, as_of=as_of)

    if profile["role"] is None:
        return {
            "role": None,
            "gaps": [],
            "recommendations": [],
            "catalog": _catalog_meta(),
            "calculated_at": as_of,
        }

    evidence = competency_service.get_evidence(db, user_id)
    evidence_types_by_code: dict[str, set[str]] = {}
    for item in evidence:
        if item.review_status.value != "accepted":
            continue
        evidence_types_by_code.setdefault(item.competency.code, set()).add(
            item.evidence_type.value
        )

    results_by_code: dict[str, CompetencyResult] = {}
    established: set[str] = set()
    gaps: list[Gap] = []

    for entry in profile["competencies"]:
        competency = entry["competency"]
        result: CompetencyResult = entry["result"]
        results_by_code[competency.code] = result

        if result.status == CompetencyStatus.ESTABLISHED:
            established.add(competency.code)

        gap = calculate_gap(
            competency_id=competency.id,
            competency_code=competency.code,
            competency_name=competency.name,
            target_level=entry["target_level"],
            criticality=entry["criticality"],
            result=result,
        )
        if gap is not None:
            gaps.append(gap)

    ranked = rank_gaps(gaps)

    catalog = get_catalog()
    resources_for = {
        code: catalog.find_for_competency(code) for code in results_by_code
    }

    recommendations: list[Recommendation] = build_recommendations(
        gaps=ranked,
        results_by_code=results_by_code,
        evidence_types_by_code=evidence_types_by_code,
        established_codes=established,
        resources_for=resources_for,
        limit=limit,
    )

    return {
        "role": profile["role"],
        "gaps": ranked,
        "recommendations": recommendations,
        "catalog": _catalog_meta(),
        "calculated_at": as_of,
    }


def _catalog_meta() -> dict:
    catalog = get_catalog()
    return {
        "adapter": catalog.name,
        "is_live_integration": catalog.is_live_integration,
        "notice": (
            "Recommendations are drawn from a local prototype catalogue. No live "
            "iGOT Karmayogi integration is implemented in this build; the "
            "LearningCatalogAdapter interface is the point at which one would be "
            "added."
        ),
    }
