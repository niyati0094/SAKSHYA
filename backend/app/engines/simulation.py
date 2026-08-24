"""Deterministic simulation scoring.

The score is a weighted mean of expert-assigned credits. It is a lookup, not a
judgement: the credit for every option was fixed when the rubric was written.
No language model participates. The AI debrief (see `app.ai.debrief`) is
generated *after* this function returns and cannot alter its output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.simulations.catalog import Scenario


@dataclass(frozen=True)
class DecisionOutcome:
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


@dataclass(frozen=True)
class SimulationResult:
    scenario_code: str
    score: float
    max_score: float
    percentage: float
    band: str
    answered_count: int
    total_decisions: int
    outcomes: list[DecisionOutcome] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)


#: Performance bands. Expert-defined thresholds, applied to the weighted mean.
BANDS: list[tuple[float, str]] = [
    (0.85, "Strong"),
    (0.65, "Competent"),
    (0.45, "Developing"),
    (0.0, "Needs support"),
]


def band_for(percentage: float) -> str:
    for threshold, label in BANDS:
        if percentage >= threshold:
            return label
    return BANDS[-1][1]


def score_attempt(scenario: Scenario, answers: dict[str, str]) -> SimulationResult:
    """Score a set of decisions against the scenario rubric.

    Unanswered decisions score zero rather than being skipped: leaving a
    judgement unmade is itself a failure to act, and dropping them from the
    denominator would let a partial attempt score as highly as a complete one.
    """
    outcomes: list[DecisionOutcome] = []
    earned = 0.0
    available = 0.0
    answered = 0

    for decision in scenario.decisions:
        best = decision.best_option
        chosen_key = answers.get(decision.key)
        chosen = decision.option(chosen_key) if chosen_key else None

        if chosen is None:
            rationale = (
                "No decision was recorded. The best available choice was: "
                f"{best.text}"
            )
            credit = 0.0
        else:
            rationale = chosen.rationale
            credit = chosen.credit
            answered += 1

        earned += credit * decision.weight
        available += decision.weight

        outcomes.append(
            DecisionOutcome(
                decision_key=decision.key,
                prompt=decision.prompt,
                chosen_key=chosen.key if chosen else None,
                chosen_text=chosen.text if chosen else None,
                credit=credit,
                weight=decision.weight,
                rationale=rationale,
                best_key=best.key,
                best_text=best.text,
                is_best=bool(chosen and chosen.key == best.key),
                answered=chosen is not None,
            )
        )

    percentage = earned / available if available else 0.0

    return SimulationResult(
        scenario_code=scenario.code,
        score=round(earned, 4),
        max_score=round(available, 4),
        percentage=round(percentage, 4),
        band=band_for(percentage),
        answered_count=answered,
        total_decisions=len(scenario.decisions),
        outcomes=outcomes,
        explanation=_explain(scenario, outcomes, earned, available, percentage),
    )


def _explain(
    scenario: Scenario,
    outcomes: list[DecisionOutcome],
    earned: float,
    available: float,
    percentage: float,
) -> list[str]:
    best_count = sum(1 for outcome in outcomes if outcome.is_best)
    unanswered = [outcome for outcome in outcomes if not outcome.answered]

    lines = [
        f"Score {earned:.2f} of {available:.2f} ({percentage:.0%}) — {band_for(percentage)}.",
        (
            f"{best_count} of {len(outcomes)} decisions matched the strongest option "
            "in the expert rubric."
        ),
    ]

    if unanswered:
        lines.append(
            f"{len(unanswered)} decision(s) were left unanswered and scored zero."
        )

    weakest = min(
        (outcome for outcome in outcomes if outcome.answered),
        key=lambda outcome: outcome.credit,
        default=None,
    )
    if weakest is not None and weakest.credit < 1.0:
        lines.append(
            f"Weakest decision: “{weakest.prompt}” — the stronger choice was: "
            f"{weakest.best_text}"
        )

    lines.append(
        "Every credit above was fixed in the scenario rubric before this attempt. "
        "The score is a weighted mean of those credits, not a model judgement."
    )
    return lines
