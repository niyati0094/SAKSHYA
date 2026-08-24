"""Simulation lab endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.engines.simulation import score_attempt
from app.models.user import User
from app.services import simulation_service as service
from app.simulations.catalog import SCENARIOS, Scenario, get_scenario

router = APIRouter(prefix="/simulations", tags=["simulations"])

PROTOTYPE_NOTICE = (
    "Prototype scenario. Illustrative teaching content and rubric written for "
    "this prototype; not official Government of India training material."
)

SCORING_NOTE = (
    "Scored deterministically against the scenario's expert-defined rubric. "
    "Every option's credit was fixed before this attempt. The narrative debrief "
    "was generated afterwards and did not influence the score."
)


class OptionOut(BaseModel):
    key: str
    text: str


class DecisionOut(BaseModel):
    key: str
    prompt: str
    context: str
    options: list[OptionOut]


class ScenarioSummaryOut(BaseModel):
    code: str
    title: str
    summary: str
    competency_code: str
    estimated_minutes: int
    decision_count: int


class ScenarioDetailOut(ScenarioSummaryOut):
    briefing: str
    decisions: list[DecisionOut]
    prototype_notice: str


class SubmitRequest(BaseModel):
    #: {decision_key: option_key}
    answers: dict[str, str] = Field(default_factory=dict)


class OutcomeOut(BaseModel):
    decision_key: str
    prompt: str
    chosen_key: str | None
    chosen_text: str | None
    credit: float
    weight: float
    rationale: str
    best_key: str
    best_text: str
    is_best: bool
    answered: bool


class AttemptResultOut(BaseModel):
    attempt_id: int
    scenario_code: str
    scenario_title: str
    score: float
    max_score: float
    percentage: float
    band: str
    answered_count: int
    total_decisions: int
    outcomes: list[OutcomeOut]
    explanation: list[str]
    debrief: str | None
    evidence_id: int | None
    competency_code: str
    scoring_note: str


class AttemptSummaryOut(BaseModel):
    id: int
    scenario_code: str
    scenario_title: str
    percentage: float
    band: str
    completed_at: str
    evidence_id: int | None


def _summary(scenario: Scenario) -> ScenarioSummaryOut:
    return ScenarioSummaryOut(
        code=scenario.code,
        title=scenario.title,
        summary=scenario.summary,
        competency_code=scenario.competency_code,
        estimated_minutes=scenario.estimated_minutes,
        decision_count=len(scenario.decisions),
    )


@router.get("", response_model=list[ScenarioSummaryOut])
def list_scenarios(_: User = Depends(get_current_user)) -> list[ScenarioSummaryOut]:
    return [_summary(scenario) for scenario in SCENARIOS]


@router.get("/attempts/mine", response_model=list[AttemptSummaryOut])
def my_attempts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AttemptSummaryOut]:
    out: list[AttemptSummaryOut] = []
    for attempt in service.list_attempts(db, current_user.id):
        scenario = get_scenario(attempt.scenario_code)
        out.append(
            AttemptSummaryOut(
                id=attempt.id,
                scenario_code=attempt.scenario_code,
                scenario_title=scenario.title if scenario else attempt.scenario_code,
                percentage=attempt.percentage,
                band=attempt.band,
                completed_at=attempt.completed_at.isoformat(),
                evidence_id=attempt.evidence_id,
            )
        )
    return out


@router.get("/attempts/{attempt_id}", response_model=AttemptResultOut)
def get_attempt(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptResultOut:
    attempt = service.get_attempt(db, attempt_id, current_user.id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    scenario = get_scenario(attempt.scenario_code)
    if scenario is None:  # pragma: no cover - scenario removed after an attempt
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    # Re-derive the per-decision breakdown from the stored answers. The stored
    # score is returned as recorded rather than recomputed, so a later rubric
    # change cannot silently rewrite history.
    result = score_attempt(scenario, json.loads(attempt.answers_json))

    return AttemptResultOut(
        attempt_id=attempt.id,
        scenario_code=scenario.code,
        scenario_title=scenario.title,
        score=attempt.score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        band=attempt.band,
        answered_count=result.answered_count,
        total_decisions=result.total_decisions,
        outcomes=[OutcomeOut(**outcome.__dict__) for outcome in result.outcomes],
        explanation=result.explanation,
        debrief=attempt.debrief,
        evidence_id=attempt.evidence_id,
        competency_code=scenario.competency_code,
        scoring_note=SCORING_NOTE,
    )


@router.get("/{scenario_code}", response_model=ScenarioDetailOut)
def get_scenario_detail(
    scenario_code: str, _: User = Depends(get_current_user)
) -> ScenarioDetailOut:
    scenario = get_scenario(scenario_code)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    return ScenarioDetailOut(
        **_summary(scenario).model_dump(),
        briefing=scenario.briefing,
        # Credits and rationales are withheld until after submission, so the
        # correct answer cannot be read out of the payload.
        decisions=[
            DecisionOut(
                key=decision.key,
                prompt=decision.prompt,
                context=decision.context,
                options=[
                    OptionOut(key=option.key, text=option.text) for option in decision.options
                ],
            )
            for decision in scenario.decisions
        ],
        prototype_notice=PROTOTYPE_NOTICE,
    )


@router.post(
    "/{scenario_code}/submit",
    response_model=AttemptResultOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_attempt(
    scenario_code: str,
    payload: SubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptResultOut:
    """Score an attempt and write the resulting evidence to the ledger."""
    try:
        attempt, result, scenario, evidence = service.run_attempt(
            db,
            user_id=current_user.id,
            scenario_code=scenario_code,
            answers=payload.answers,
        )
    except service.UnknownScenarioError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found"
        ) from None

    return AttemptResultOut(
        attempt_id=attempt.id,
        scenario_code=scenario.code,
        scenario_title=scenario.title,
        score=result.score,
        max_score=result.max_score,
        percentage=result.percentage,
        band=result.band,
        answered_count=result.answered_count,
        total_decisions=result.total_decisions,
        outcomes=[OutcomeOut(**outcome.__dict__) for outcome in result.outcomes],
        explanation=result.explanation,
        debrief=attempt.debrief,
        evidence_id=evidence.id if evidence else None,
        competency_code=scenario.competency_code,
        scoring_note=SCORING_NOTE,
    )
