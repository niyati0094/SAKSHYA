"""Organisation-level aggregation for the admin dashboard.

Aggregates are computed by running the same deterministic engines over every
learner's evidence, then counting. No separate analytics model exists, so an
organisation-level figure can never disagree with the individual profiles it
is built from.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.competency import CompetencyStatus
from app.engines.gap import rank_gaps
from app.models.competency import LearnerProfile, StatisticalRole
from app.models.user import User, UserRole
from app.services import pathway_service


def organisation_overview(db: Session, *, as_of: datetime | None = None) -> dict:
    as_of = as_of or datetime.now(timezone.utc)

    learners = list(
        db.scalars(select(User).where(User.role == UserRole.LEARNER, User.is_active.is_(True)))
    )

    per_competency: dict[str, dict] = {}
    role_counts: dict[str, int] = {}
    learners_with_profile = 0
    total_gaps = 0
    urgent_gaps = 0

    for learner in learners:
        profile = db.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == learner.id)
        )
        if profile is None:
            continue
        learners_with_profile += 1

        role = db.get(StatisticalRole, profile.statistical_role_id)
        if role is not None:
            role_counts[role.name] = role_counts.get(role.name, 0) + 1

        pathway = pathway_service.build_pathway(db, learner.id, limit=50, as_of=as_of)

        for gap in rank_gaps(pathway["gaps"]):
            total_gaps += 1
            if gap.severity_band == "urgent":
                urgent_gaps += 1

            bucket = per_competency.setdefault(
                gap.competency_code,
                {
                    "competency_code": gap.competency_code,
                    "competency_name": gap.competency_name,
                    "criticality": gap.criticality,
                    "learners_with_gap": 0,
                    "learners_unproven": 0,
                    "severity_total": 0.0,
                    "target_level": gap.target_level,
                },
            )
            bucket["learners_with_gap"] += 1
            bucket["severity_total"] += gap.severity
            if gap.status in {
                CompetencyStatus.NO_EVIDENCE,
                CompetencyStatus.INSUFFICIENT_EVIDENCE,
            }:
                bucket["learners_unproven"] += 1

    training_needs = []
    for bucket in per_competency.values():
        count = bucket["learners_with_gap"]
        training_needs.append(
            {
                "competency_code": bucket["competency_code"],
                "competency_name": bucket["competency_name"],
                "criticality": bucket["criticality"],
                "target_level": bucket["target_level"],
                "learners_with_gap": count,
                "learners_unproven": bucket["learners_unproven"],
                "average_severity": round(bucket["severity_total"] / count, 4),
                "share_of_learners": (
                    round(count / learners_with_profile, 4) if learners_with_profile else 0.0
                ),
            }
        )

    # Most widespread first, then most severe. Deterministic tie-break by code.
    training_needs.sort(
        key=lambda item: (
            -item["learners_with_gap"],
            -item["average_severity"],
            item["competency_code"],
        )
    )

    return {
        "learner_count": len(learners),
        "learners_with_profile": learners_with_profile,
        "total_gaps": total_gaps,
        "urgent_gaps": urgent_gaps,
        "role_distribution": [
            {"role_name": name, "learner_count": count}
            for name, count in sorted(role_counts.items(), key=lambda pair: -pair[1])
        ],
        "training_needs": training_needs,
        "calculated_at": as_of,
        "notice": (
            "Aggregated from the same deterministic engine that produces each "
            "learner's profile. Prototype sample cohort."
        ),
    }
