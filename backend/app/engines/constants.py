"""Expert-defined constants for the deterministic competency engine.

Every number that influences a competency result lives here, in one auditable
place. Nothing in this module is learned, inferred, or produced by an AI model.
Changing a value here changes scoring for the whole system - which is exactly
why they are centralised rather than scattered through the calculation.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Competency levels
# --------------------------------------------------------------------------
# A four-level progression. Mastery is a continuous 0..1 estimate; these bands
# translate it into the level language used by role requirements.

LEVEL_LABELS: dict[int, str] = {
    0: "Not established",
    1: "Awareness",
    2: "Working",
    3: "Proficient",
    4: "Expert",
}

# Lower bound of each level. Mastery below LEVEL_BANDS[1] is level 0.
LEVEL_BANDS: dict[int, float] = {
    1: 0.00,
    2: 0.40,
    3: 0.60,
    4: 0.80,
}

# --------------------------------------------------------------------------
# Evidence type weights
# --------------------------------------------------------------------------
# The core thesis of SAKSHYA is expressed here: completing a course is the
# WEAKEST form of evidence, because attendance is not demonstrated capability.
# Evidence where the learner actually did the work under observation - a
# simulation, or a submission reviewed by a subject matter expert - carries the
# most weight.

EVIDENCE_TYPE_WEIGHTS: dict[str, float] = {
    "simulation": 1.5,          # made real decisions in a scenario
    "practical_submission": 1.4,  # produced work, reviewed by an SME
    "sme_verified": 1.2,        # expert attested to observed capability
    "assessment": 1.0,          # answered questions correctly (baseline)
    "peer_review": 0.8,         # colleague assessment
    "course_completion": 0.4,   # attendance only - deliberately weak
}

DEFAULT_EVIDENCE_WEIGHT = 1.0

# --------------------------------------------------------------------------
# Recency decay
# --------------------------------------------------------------------------
# Capability decays if never re-demonstrated. Evidence loses half its influence
# every RECENCY_HALF_LIFE_DAYS, but never falls below the floor: old evidence
# still counts for something.

RECENCY_HALF_LIFE_DAYS = 365.0
RECENCY_FLOOR = 0.10

# --------------------------------------------------------------------------
# Confidence model
# --------------------------------------------------------------------------
# Confidence answers "how much should we trust this mastery estimate?" and is
# deliberately separate from mastery itself. A high score from a single stale
# quiz should NOT read the same as a high score from varied, recent evidence.
#
# Four components, each 0..1, combined with the weights below (they sum to 1.0).

CONFIDENCE_WEIGHTS: dict[str, float] = {
    "volume": 0.35,     # how much effective evidence exists
    "diversity": 0.25,  # how many distinct kinds of evidence
    "recency": 0.20,    # how recent the strongest evidence is
    "agreement": 0.20,  # how consistent the evidence is with itself
}

# Effective evidence weight at which the volume component saturates.
CONFIDENCE_TARGET_EFFECTIVE_EVIDENCE = 3.0

# Number of distinct evidence types at which diversity saturates.
CONFIDENCE_TARGET_TYPE_COUNT = 3

# Score spread (population standard deviation) at which agreement reaches zero.
CONFIDENCE_MAX_DISPERSION = 0.35

# With a single evidence item, self-consistency is unknowable. Use a neutral
# value rather than rewarding or punishing the learner for it.
CONFIDENCE_SINGLE_ITEM_AGREEMENT = 0.5

# --------------------------------------------------------------------------
# Sufficiency thresholds
# --------------------------------------------------------------------------
# Below either threshold the system reports INSUFFICIENT_EVIDENCE instead of
# asserting a level. Saying "I do not know yet" is a first-class outcome.

MIN_EFFECTIVE_EVIDENCE = 1.5
MIN_CONFIDENCE = 0.35

# --------------------------------------------------------------------------
# Review gating
# --------------------------------------------------------------------------
# Only accepted evidence contributes to a competency estimate. Pending and
# rejected evidence remains visible in the ledger - it is part of the audit
# trail - but it does not move the number.

COUNTED_REVIEW_STATUSES: frozenset[str] = frozenset({"accepted"})
