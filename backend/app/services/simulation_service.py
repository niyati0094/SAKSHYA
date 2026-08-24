"""Running simulations and turning performance into evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.debrief import build_debrief
from app.engines.simulation import SimulationResult, score_attempt
from app.models.competency import Competency
from app.models.evidence import Evidence, EvidenceType, ReviewStatus
from app.models.simulation import SimulationAttempt
from app.simulations.catalog import Scenario, get_scenario


class UnknownScenarioError(LookupError):
    pass


def run_attempt(
    db: Session,
    *,
    user_id: int,
    scenario_code: str,
    answers: dict[str, str],
) -> tuple[SimulationAttempt, SimulationResult, Scenario, Evidence | None]:
    """Score an attempt, record it, and generate the resulting evidence.

    Ordering matters and is deliberate: the deterministic engine scores first,
    evidence is written from that score, and only then is a narrative debrief
    produced. The debrief can never influence what was recorded.
    """
    scenario = get_scenario(scenario_code)
    if scenario is None:
        raise UnknownScenarioError(scenario_code)

    result = score_attempt(scenario, answers)

    evidence = _record_evidence(db, user_id=user_id, scenario=scenario, result=result)

    attempt = SimulationAttempt(
        user_id=user_id,
        scenario_code=scenario.code,
        answers_json=json.dumps(answers, sort_keys=True),
        score=result.score,
        max_score=result.max_score,
        percentage=result.percentage,
        band=result.band,
        debrief=build_debrief(scenario, result),
        evidence_id=evidence.id if evidence else None,
        is_prototype_data=True,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt, result, scenario, evidence


def _record_evidence(
    db: Session, *, user_id: int, scenario: Scenario, result: SimulationResult
) -> Evidence | None:
    """Write the simulation outcome into the evidence ledger.

    Simulation evidence is accepted immediately because it was scored against
    a fixed expert rubric - there is no model judgement for a reviewer to
    check. Its weight (1.5, the highest of any evidence type) reflects that
    the learner made real decisions rather than recognising an answer.
    """
    competency = db.scalar(
        select(Competency).where(Competency.code == scenario.competency_code)
    )
    if competency is None:
        return None

    evidence = Evidence(
        user_id=user_id,
        competency_id=competency.id,
        evidence_type=EvidenceType.SIMULATION,
        activity_title=f"{scenario.title} — simulation",
        source="SAKSHYA simulation lab (prototype)",
        raw_score=result.score,
        max_score=result.max_score,
        review_status=ReviewStatus.ACCEPTED,
        notes=(
            f"Scored {result.percentage:.0%} ({result.band}) against the scenario's "
            f"expert rubric across {result.total_decisions} decisions."
        ),
        observed_at=datetime.now(timezone.utc),
        is_prototype_data=True,
    )
    db.add(evidence)
    db.flush()
    return evidence


def list_attempts(db: Session, user_id: int) -> list[SimulationAttempt]:
    return list(
        db.scalars(
            select(SimulationAttempt)
            .where(SimulationAttempt.user_id == user_id)
            .order_by(SimulationAttempt.completed_at.desc())
        )
    )


def get_attempt(db: Session, attempt_id: int, user_id: int) -> SimulationAttempt | None:
    attempt = db.get(SimulationAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        return None
    return attempt
