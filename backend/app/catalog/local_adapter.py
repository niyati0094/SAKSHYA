"""Prototype learning catalogue backed by sample resources.

PROTOTYPE SAMPLE CONTENT. These resources are illustrative entries written for
this prototype. They are not real iGOT Karmayogi courses, and none of the
titles below refer to an actual published course. Every entry is flagged
`is_prototype_data=True` and carries the provider name
"Local prototype catalogue" so it cannot be presented as an iGOT resource.
"""

from __future__ import annotations

from app.catalog.base import LearningResource, ResourceKind

PROVIDER = "Local prototype catalogue"

RESOURCES: list[LearningResource] = [
    # --- Sampling design ---
    LearningResource(
        "LOC-SAMP-L1",
        "Sampling Frames and Selection Probabilities",
        "How frames are built, what undercoverage and duplication do to "
        "selection probabilities, and why weights are their reciprocal.",
        ResourceKind.LEARN,
        "COMP-SAMP",
        2,
        45,
        PROVIDER,
    ),
    LearningResource(
        "LOC-SAMP-L2",
        "Stratification and Allocation in Practice",
        "Choosing strata, proportional versus Neyman allocation, and when "
        "disproportionate allocation is justified.",
        ResourceKind.LEARN,
        "COMP-SAMP",
        3,
        60,
        PROVIDER,
        prerequisites=("COMP-SAMP",),
    ),
    LearningResource(
        "LOC-SAMP-P1",
        "Variance Estimation Workbook",
        "Worked exercises computing design-consistent estimates and their "
        "standard errors for stratified designs.",
        ResourceKind.PRACTICE,
        "COMP-SAMP",
        3,
        40,
        PROVIDER,
    ),
    LearningResource(
        "SIM-SAMP",
        "Simulation: choosing a sampling design under a fixed budget",
        "Design a sample where a small stratum needs its own reliable estimate, "
        "and defend the allocation and estimation choices.",
        ResourceKind.PROVE,
        "COMP-SAMP",
        3,
        6,
        PROVIDER,
    ),
    # --- Non-response ---
    LearningResource(
        "LOC-NRES-L1",
        "Diagnosing Unit and Item Non-Response",
        "Telling the two apart, why the response rate alone does not measure "
        "bias, and what auxiliary frame data can tell you.",
        ResourceKind.LEARN,
        "COMP-NRES",
        2,
        40,
        PROVIDER,
    ),
    LearningResource(
        "LOC-NRES-P1",
        "Weighting Class Adjustment Exercise",
        "Build weighting classes from frame variables, compute adjustment "
        "factors, and handle classes that fall below the minimum size.",
        ResourceKind.PRACTICE,
        "COMP-NRES",
        3,
        50,
        PROVIDER,
    ),
    LearningResource(
        "SIM-NRES",
        "Simulation: rising non-response in a household survey",
        "Diagnose a falling response rate, choose an adjustment, and decide "
        "what the methodology note must disclose.",
        ResourceKind.PROVE,
        "COMP-NRES",
        3,
        6,
        PROVIDER,
    ),
    # --- Administrative data ---
    LearningResource(
        "LOC-ADMIN-L1",
        "Reconciling Administrative Registers with Survey Data",
        "Definitional differences, reference periods, and why a full count of "
        "the wrong population is still wrong.",
        ResourceKind.LEARN,
        "COMP-ADMIN",
        2,
        35,
        PROVIDER,
    ),
    LearningResource(
        "SIM-ADMIN",
        "Simulation: administrative data inconsistency before publication",
        "Resolve a register-versus-survey discrepancy days before release and "
        "decide what to publish.",
        ResourceKind.PROVE,
        "COMP-ADMIN",
        2,
        5,
        PROVIDER,
    ),
    # --- Data quality ---
    LearningResource(
        "LOC-DQA-L1",
        "Editing Rules and Selective Editing",
        "Validity, consistency and outlier edits, and concentrating effort on "
        "the errors that move published estimates.",
        ResourceKind.LEARN,
        "COMP-DQA",
        3,
        45,
        PROVIDER,
    ),
    LearningResource(
        "LOC-DQA-P1",
        "Editing Rule Set Submission",
        "Draft and document an edit rule set for a price collection dataset, "
        "reviewed by a subject matter expert.",
        ResourceKind.PRACTICE,
        "COMP-DQA",
        3,
        90,
        PROVIDER,
    ),
    # --- Questionnaire design ---
    LearningResource(
        "LOC-QDES-L1",
        "Designing Survey Instruments",
        "Question wording, response formats, skip logic and respondent burden.",
        ResourceKind.LEARN,
        "COMP-QDES",
        2,
        40,
        PROVIDER,
    ),
    # --- Disclosure control ---
    LearningResource(
        "LOC-SDC-L1",
        "Statistical Disclosure Control Essentials",
        "Primary and secondary suppression, dominance rules, and perturbative "
        "alternatives.",
        ResourceKind.LEARN,
        "COMP-SDC",
        2,
        35,
        PROVIDER,
    ),
    LearningResource(
        "LOC-SDC-P1",
        "Table Suppression Exercise",
        "Apply threshold and dominance rules to a draft publication table.",
        ResourceKind.PRACTICE,
        "COMP-SDC",
        2,
        30,
        PROVIDER,
    ),
]


class LocalCatalogAdapter:
    """Prototype catalogue. Satisfies `LearningCatalogAdapter`."""

    name = PROVIDER
    #: Explicitly False. No live external integration exists in this build.
    is_live_integration = False

    def find_for_competency(
        self, competency_code: str, *, kind: str | None = None
    ) -> list[LearningResource]:
        return [
            resource
            for resource in RESOURCES
            if resource.competency_code == competency_code
            and (kind is None or resource.kind == kind)
        ]

    def all_resources(self) -> list[LearningResource]:
        return list(RESOURCES)
