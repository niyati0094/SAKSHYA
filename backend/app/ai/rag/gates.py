"""Verification gates for generated assessment items.

Generation is treated as a verification problem, not a generation problem. An
item is not published because a model produced it; it is published because it
survived every gate, and the gate that rejected it is recorded by name.

    G1  Grounding            key entailed by the cited passage alone
    G2  Single-answer        no distractor also entailed by the passage
    G3  Anchor preservation  population / period / unit / denominator / assumption
    G4  Structural sanity    no "all of the above", no length giveaway, no duplicates
    G5  Novelty              not a near-duplicate of an existing bank item

A system that never rejects anything is not verifying anything, so the
rejection rate - and which gate dominates - is reported rather than hidden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai.rag.anchors import check_anchor_preservation
from app.ai.rag.ground import verify_question
from app.models.question import GroundingStatus

GATE_NAMES: dict[str, str] = {
    "G1": "Grounding",
    "G2": "Single-answer",
    "G3": "Anchor preservation",
    "G4": "Structural sanity",
    "G5": "Novelty",
}

#: Cosine similarity at or above which two items are treated as near-duplicates.
NOVELTY_THRESHOLD = 0.97

_BANNED_OPTION_RE = re.compile(
    r"^\s*(all|none) of the above\b|^\s*both\s+[ab]\s+and\b", re.IGNORECASE
)


@dataclass(frozen=True)
class GateOutcome:
    gate: str
    name: str
    passed: bool
    note: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    #: The first gate that failed, e.g. "G3". None when everything passed.
    failed_gate: str | None
    grounding_status: GroundingStatus
    grounding_score: float
    note: str | None
    outcomes: list[GateOutcome] = field(default_factory=list)

    @property
    def failed_gate_name(self) -> str | None:
        return GATE_NAMES.get(self.failed_gate) if self.failed_gate else None


def _structural_check(stem: str, options: list[str]) -> GateOutcome:
    """Pure rules. No model involved, and none needed."""
    problems: list[str] = []

    if len({option.strip().lower() for option in options}) != len(options):
        problems.append("duplicate options")

    if any(_BANNED_OPTION_RE.search(option) for option in options):
        problems.append("'all/none of the above' style option")

    lengths = [len(option) for option in options]
    if len(lengths) >= 3 and max(lengths) > 2.5 * (sum(lengths) / len(lengths)):
        # A conspicuously long option is a well-known answer giveaway.
        problems.append("one option is far longer than the others")

    if stem.count(" not ") > 1 or ("not" in stem.lower() and "except" in stem.lower()):
        problems.append("double negative in the stem")

    if problems:
        return GateOutcome("G4", GATE_NAMES["G4"], False, "; ".join(problems))
    return GateOutcome("G4", GATE_NAMES["G4"], True)


def _novelty_check(
    item_text: str, existing_vectors: list[list[float]], embedder
) -> GateOutcome:
    if not existing_vectors:
        return GateOutcome("G5", GATE_NAMES["G5"], True)

    vector = embedder.embed([item_text])[0]
    best = max(
        sum(a * b for a, b in zip(vector, other, strict=True))
        for other in existing_vectors
    )
    if best >= NOVELTY_THRESHOLD:
        return GateOutcome(
            "G5",
            GATE_NAMES["G5"],
            False,
            f"near-duplicate of an existing item (similarity {best:.2f})",
        )
    return GateOutcome("G5", GATE_NAMES["G5"], True)


def verify_item(
    *,
    stem: str,
    options: list[str],
    correct_index: int,
    source_quote: str,
    chunk_text: str,
    existing_vectors: list[list[float]] | None = None,
    embedder=None,
) -> VerificationResult:
    """Run every gate. The first failure decides the verdict, but all outcomes
    are returned so a reviewer can see the full picture."""
    outcomes: list[GateOutcome] = []
    correct_option = options[correct_index]

    # --- G1 + G2: grounding of the key, and uniqueness of the answer ---------
    grounding = verify_question(
        source_quote=source_quote, correct_option=correct_option, chunk_text=chunk_text
    )
    outcomes.append(
        GateOutcome("G1", GATE_NAMES["G1"], grounding.is_grounded, grounding.note)
    )

    # A distractor that is also supported by the passage means the item has two
    # defensible answers.
    from app.ai.rag.ground import verify_quote

    rival = next(
        (
            option
            for index, option in enumerate(options)
            if index != correct_index and verify_quote(option, chunk_text).is_grounded
        ),
        None,
    )
    outcomes.append(
        GateOutcome(
            "G2",
            GATE_NAMES["G2"],
            rival is None,
            None
            if rival is None
            else f"a distractor is also supported by the passage: “{rival[:80]}”",
        )
    )

    # --- G3: the statistics-specific gate -----------------------------------
    anchors = check_anchor_preservation(
        passage=chunk_text, item_text=f"{stem} {correct_option}"
    )
    outcomes.append(GateOutcome("G3", GATE_NAMES["G3"], anchors.passed, anchors.note))

    # --- G4 + G5 ------------------------------------------------------------
    outcomes.append(_structural_check(stem, options))
    if embedder is not None:
        outcomes.append(_novelty_check(f"{stem} {correct_option}", existing_vectors or [], embedder))

    failure = next((outcome for outcome in outcomes if not outcome.passed), None)

    if failure is None:
        return VerificationResult(
            passed=True,
            failed_gate=None,
            grounding_status=GroundingStatus.GROUNDED,
            grounding_score=grounding.score,
            note=None,
            outcomes=outcomes,
        )

    return VerificationResult(
        passed=False,
        failed_gate=failure.gate,
        grounding_status=GroundingStatus.UNGROUNDED,
        grounding_score=grounding.score,
        note=f"[{failure.gate} {failure.name}] {failure.note}",
        outcomes=outcomes,
    )
