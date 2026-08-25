"""Context-anchor preservation — the statistics-specific verification gate.

In official statistics a definition stripped of its qualifying context is not
merely incomplete, it is *wrong*. "Average monthly expenditure was 4,200" means
nothing without knowing the population it covers, the reference period it
applies to, the unit of analysis, or the denominator it was divided by.

Generic question generators are built for trivia and have no concept of this.
They will happily turn

    "Among rural households, average monthly per-capita expenditure in
     2023-24 was 4,200 rupees."

into

    "What was average monthly expenditure?"  ->  "4,200 rupees"

which is a factually wrong question generated from a factually correct
passage. This gate exists to catch exactly that.

The approach is deliberately split:

* Identifying *which* anchors a passage's claim depends on is a reading task.
* Checking whether the generated item *preserves* them is a deterministic
  string/rule check.

So the extraction step is where a language model would be used, and the
verdict is always arithmetic over what was found. In this offline build the
extraction is lexical - documented honestly below - and the interface is the
same one a hosted model would slot into.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Anchor definitions
# --------------------------------------------------------------------------
# Each anchor is recognised by the vocabulary a statistical passage uses when
# it depends on that anchor. These are matched against the SOURCE passage to
# decide which anchors the claim requires, then against the generated ITEM to
# decide whether they survived.


@dataclass(frozen=True)
class AnchorSpec:
    name: str
    #: Human-readable description, shown to a reviewer when the gate fails.
    description: str
    patterns: tuple[str, ...]


ANCHOR_SPECS: tuple[AnchorSpec, ...] = (
    AnchorSpec(
        "population",
        "who or what the figure covers",
        (
            r"\b(?:rural|urban|male|female)\b",
            r"\bhouseholds?\b",
            r"\benterprises?\b",
            r"\bestablishments?\b",
            r"\brespondents?\b",
            r"\btarget population\b",
            r"\bpersons? aged\b",
            r"\bamong\b",
        ),
    ),
    AnchorSpec(
        "reference_period",
        "the time period the figure applies to",
        (
            r"\b(?:19|20)\d{2}\s*[-–]\s*\d{2,4}\b",   # 2023-24, 2023–2024
            r"\b(?:19|20)\d{2}\b",
            r"\b(?:annual|monthly|weekly|daily|quarterly)\b",
            r"\breference period\b",
            r"\blast \d+ (?:days|months|years)\b",
            r"\bper (?:month|year|week|day)\b",
        ),
    ),
    AnchorSpec(
        "unit_of_analysis",
        "the unit the figure is measured on",
        (
            r"\bper[- ]capita\b",
            r"\bper household\b",
            r"\bper worker\b",
            r"\bper enterprise\b",
            r"\bunit of analysis\b",
            r"\bunits?\b",
        ),
    ),
    AnchorSpec(
        "denominator",
        "what the figure was divided by",
        (
            r"\bdenominator\b",
            r"\bper 1,?000\b",
            r"\bper cent\b|\bpercent(?:age)?\b",
            r"\brate\b",
            r"\bratio\b",
            r"\bproportion\b",
            r"\bshare of\b",
            r"\bout of\b",
        ),
    ),
    AnchorSpec(
        "assumption",
        "the condition the claim depends on",
        (
            r"\bassum(?:e|es|ing|ption)\b",
            r"\bprovided that\b",
            r"\bconditional on\b",
            r"\bmissing[- ]at[- ]random\b",
            r"\bsubject to\b",
            r"\bwhere\b.{0,20}\bholds\b",
        ),
    ),
)

#: An anchor is only *required* when the passage makes a quantitative or
#: definitional claim. Narrative prose does not need a denominator.
_CLAIM_RE = re.compile(
    r"\d|\bis defined as\b|\bmeans\b|\brefers to\b|\brate\b|\bratio\b|\baverage\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AnchorResult:
    required: list[str]
    preserved: list[str]
    missing: list[str]
    passed: bool
    note: str | None = None
    details: dict[str, str] = field(default_factory=dict)


def _present(text: str, spec: AnchorSpec) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in spec.patterns)


def required_anchors(passage: str) -> list[str]:
    """Which anchors this passage's claim depends on.

    Returns nothing for prose that makes no quantitative or definitional claim -
    demanding a denominator from a narrative sentence would be noise.
    """
    if not _CLAIM_RE.search(passage):
        return []
    return [spec.name for spec in ANCHOR_SPECS if _present(passage, spec)]


def check_anchor_preservation(*, passage: str, item_text: str) -> AnchorResult:
    """Verify the generated item carries the context its source claim needs.

    `item_text` should be the stem plus the correct option: an anchor stated in
    either place is preserved.
    """
    specs = {spec.name: spec for spec in ANCHOR_SPECS}
    required = required_anchors(passage)

    if not required:
        return AnchorResult(
            required=[],
            preserved=[],
            missing=[],
            passed=True,
            note=None,
        )

    preserved = [name for name in required if _present(item_text, specs[name])]
    missing = [name for name in required if name not in preserved]

    if not missing:
        return AnchorResult(required, preserved, [], True, None)

    described = ", ".join(f"{name} ({specs[name].description})" for name in missing)
    return AnchorResult(
        required=required,
        preserved=preserved,
        missing=missing,
        passed=False,
        note=(
            f"The source passage's claim depends on {len(required)} context "
            f"anchor(s); the question drops {len(missing)}: {described}. A "
            "statistical claim without its context is not incomplete, it is "
            "wrong - so this item is rejected rather than published."
        ),
        details={name: specs[name].description for name in missing},
    )
