"""Bridges stored evidence to the deterministic competency engine.

This layer does the I/O; `app.engines.competency` does the arithmetic. Keeping
them apart is what makes the scoring reproducible and unit-testable without a
database.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.engines.competency import (
    CompetencyResult,
    EvidenceInput,
    calculate_competency,
)
from app.models.competency import (
    Competency,
    LearnerProfile,
    RoleCompetency,
    StatisticalRole,
)
from app.models.evidence import Evidence


def _utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; normalise so arithmetic is safe."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def to_engine_input(evidence: Evidence) -> EvidenceInput:
    return EvidenceInput(
        evidence_id=evidence.id,
        evidence_type=evidence.evidence_type.value,
        score=evidence.normalized_score,
        observed_at=_utc(evidence.observed_at),
        review_status=evidence.review_status.value,
        weight_override=evidence.weight_override,
    )


def get_profile(db: Session, user_id: int) -> LearnerProfile | None:
    return db.scalar(
        select(LearnerProfile)
        .where(LearnerProfile.user_id == user_id)
        .options(selectinload(LearnerProfile.statistical_role))
    )


def get_role_competencies(db: Session, role_id: int) -> list[RoleCompetency]:
    return list(
        db.scalars(
            select(RoleCompetency)
            .where(RoleCompetency.role_id == role_id)
            .options(selectinload(RoleCompetency.competency))
            .order_by(RoleCompetency.sequence, RoleCompetency.id)
        )
    )


def get_evidence(
    db: Session,
    user_id: int,
    competency_id: int | None = None,
) -> list[Evidence]:
    statement = (
        select(Evidence)
        .where(Evidence.user_id == user_id)
        .options(selectinload(Evidence.competency))
        .order_by(Evidence.observed_at.desc(), Evidence.id.desc())
    )
    if competency_id is not None:
        statement = statement.where(Evidence.competency_id == competency_id)
    return list(db.scalars(statement))


def calculate_for_competency(
    db: Session,
    user_id: int,
    competency_id: int,
    as_of: datetime | None = None,
) -> tuple[CompetencyResult, list[Evidence]]:
    """Run the engine over one competency's evidence.

    Returns both the result and the underlying evidence rows so callers can
    show the audit trail alongside the number.
    """
    as_of = as_of or datetime.now(timezone.utc)
    evidence = get_evidence(db, user_id, competency_id)
    result = calculate_competency(
        competency_id=competency_id,
        evidence=[to_engine_input(item) for item in evidence],
        as_of=as_of,
    )
    return result, evidence


def build_competency_profile(
    db: Session,
    user_id: int,
    as_of: datetime | None = None,
) -> dict:
    """Assemble the learner's full competency picture against their role.

    Every competency required by the role appears, including ones with no
    evidence at all - a missing competency is information, not an empty row to
    hide.
    """
    as_of = as_of or datetime.now(timezone.utc)
    profile = get_profile(db, user_id)
    if profile is None:
        return {"role": None, "competencies": [], "summary": _summarise([])}

    links = get_role_competencies(db, profile.statistical_role_id)

    # One query for all evidence, grouped in memory: avoids a query per
    # competency when rendering the dashboard.
    all_evidence = get_evidence(db, user_id)
    by_competency: dict[int, list[Evidence]] = {}
    for item in all_evidence:
        by_competency.setdefault(item.competency_id, []).append(item)

    entries = []
    for link in links:
        evidence = by_competency.get(link.competency_id, [])
        result = calculate_competency(
            competency_id=link.competency_id,
            evidence=[to_engine_input(item) for item in evidence],
            as_of=as_of,
        )
        entries.append(
            {
                "competency": link.competency,
                "target_level": link.target_level,
                "criticality": link.criticality.value,
                "meets_target": result.level >= link.target_level,
                "result": result,
            }
        )

    return {
        "role": profile.statistical_role,
        "competencies": entries,
        "summary": _summarise(entries),
    }


def _summarise(entries: list[dict]) -> dict:
    """Headline counts for the dashboard. Plain counting, no inference."""
    total = len(entries)
    meeting = sum(1 for entry in entries if entry["meets_target"])
    insufficient = sum(
        1
        for entry in entries
        if entry["result"].status in {"insufficient_evidence", "no_evidence"}
    )
    total_evidence = sum(entry["result"].counted_evidence_count for entry in entries)

    return {
        "total_competencies": total,
        "meeting_target": meeting,
        "below_target": total - meeting,
        "insufficient_evidence": insufficient,
        "total_counted_evidence": total_evidence,
    }


def get_competency(db: Session, competency_id: int) -> Competency | None:
    return db.get(Competency, competency_id)


def get_role_link(db: Session, role_id: int, competency_id: int) -> RoleCompetency | None:
    return db.scalar(
        select(RoleCompetency).where(
            RoleCompetency.role_id == role_id,
            RoleCompetency.competency_id == competency_id,
        )
    )


def list_roles(db: Session) -> list[StatisticalRole]:
    return list(db.scalars(select(StatisticalRole).order_by(StatisticalRole.id)))


def list_competencies(db: Session) -> list[Competency]:
    return list(db.scalars(select(Competency).order_by(Competency.id)))
