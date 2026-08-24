"""Narrative debrief for a completed simulation.

The debrief is the one place a language model is allowed near a simulation,
and it is deliberately downstream: it receives an already-computed
`SimulationResult` and turns it into prose. It cannot change the score, the
band, or any credit, because scoring has already finished by the time this
runs.

The offline implementation composes the rubric's own rationale strings, so the
feedback a learner reads is the expert reasoning that produced their score
rather than a paraphrase of it.
"""

from __future__ import annotations

from app.engines.simulation import SimulationResult
from app.simulations.catalog import Scenario


def build_debrief(scenario: Scenario, result: SimulationResult) -> str:
    strong = [outcome for outcome in result.outcomes if outcome.credit >= 0.8]
    weak = [outcome for outcome in result.outcomes if outcome.credit < 0.8]

    parts: list[str] = [
        f"You scored {result.percentage:.0%} on “{scenario.title}” "
        f"({result.band.lower()}), matching the strongest rubric option on "
        f"{sum(1 for o in result.outcomes if o.is_best)} of "
        f"{result.total_decisions} decisions."
    ]

    if strong:
        parts.append("\n\nWhat you judged well:")
        for outcome in strong:
            parts.append(f"\n• {outcome.prompt} — {outcome.rationale}")

    if weak:
        parts.append("\n\nWhere your reasoning would be challenged:")
        for outcome in weak:
            parts.append(f"\n• {outcome.prompt} — {outcome.rationale}")
            if not outcome.is_best:
                parts.append(f" The stronger choice was: {outcome.best_text}")

    parts.append(
        "\n\nThis debrief explains a score that was already calculated from the "
        "scenario's expert rubric. It did not influence the score."
    )
    return "".join(parts)
