"""Statistical simulation scenarios and their expert-defined scoring rubrics.

PROTOTYPE SAMPLE CONTENT. These scenarios and rubrics are illustrative
teaching constructs written for this prototype. They are not official
Government of India training material or official methodological guidance.

Every option carries a credit assigned in advance by the rubric author, plus
the rationale for that credit. Scoring is therefore a lookup and a weighted
mean - not a judgement made at scoring time, and never a model output. The
`rationale` strings are what the learner sees in the debrief, so the feedback
is the same expert reasoning that produced the score.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Option:
    key: str
    text: str
    #: Expert-assigned credit, 0.0 to 1.0.
    credit: float
    #: Why this choice earns that credit. Shown in the debrief.
    rationale: str


@dataclass(frozen=True)
class Decision:
    key: str
    prompt: str
    context: str
    options: list[Option]
    #: Relative importance of this decision within the scenario.
    weight: float = 1.0

    def option(self, key: str) -> Option | None:
        return next((option for option in self.options if option.key == key), None)

    @property
    def best_option(self) -> Option:
        return max(self.options, key=lambda option: option.credit)


@dataclass(frozen=True)
class Scenario:
    code: str
    title: str
    summary: str
    briefing: str
    competency_code: str
    estimated_minutes: int
    decisions: list[Decision] = field(default_factory=list)

    def decision(self, key: str) -> Decision | None:
        return next((item for item in self.decisions if item.key == key), None)


NON_RESPONSE = Scenario(
    code="SIM-NRES",
    title="Rising non-response in a household survey",
    summary=(
        "A quarterly household survey has seen its response rate fall. Decide how "
        "to diagnose the problem and whether the results can be published."
    ),
    briefing=(
        "You are the officer responsible for a quarterly household expenditure "
        "survey in a sample state. The response rate has fallen from 88 percent "
        "to 71 percent over three rounds. The fall is concentrated in urban "
        "high-income blocks. Publication is due in three weeks and the estimates "
        "of average monthly expenditure look unusually low."
    ),
    competency_code="COMP-NRES",
    estimated_minutes=6,
    decisions=[
        Decision(
            key="diagnose",
            prompt="What is your first analytical step?",
            context=(
                "You have the sampling frame, the response outcome for every "
                "selected household, and auxiliary frame variables."
            ),
            weight=1.2,
            options=[
                Option(
                    "compare",
                    "Compare respondents and non-respondents on the auxiliary frame "
                    "variables available for both groups.",
                    1.0,
                    "Correct. Non-response bias depends on how respondents and "
                    "non-respondents differ, not on the response rate alone. Frame "
                    "variables are the only information you hold for both groups, so "
                    "they are where the comparison must start.",
                ),
                Option(
                    "reweight",
                    "Apply a weighting class adjustment immediately to restore the "
                    "expected totals.",
                    0.3,
                    "Premature. Adjusting before diagnosing assumes the missing-at-random "
                    "condition holds rather than checking it. The adjustment may be "
                    "correct, but you cannot yet justify it.",
                ),
                Option(
                    "topup",
                    "Draw a top-up sample from the same frame to restore the achieved "
                    "sample size.",
                    0.2,
                    "This fixes the sample size, not the bias. Fresh selections from the "
                    "same frame will exhibit the same differential response pattern.",
                ),
                Option(
                    "publish",
                    "Publish with a footnote recording the lower response rate.",
                    0.0,
                    "A footnote does not discharge the obligation to assess bias. A "
                    "71 percent response rate concentrated in one stratum is a specific, "
                    "investigable risk.",
                ),
            ],
        ),
        Decision(
            key="adjust",
            prompt=(
                "The comparison confirms urban high-income households are markedly "
                "under-represented. How do you adjust?"
            ),
            context=(
                "Sector and income band are available on the frame for every selected "
                "household, responding or not."
            ),
            weight=1.3,
            options=[
                Option(
                    "classes",
                    "Form weighting classes from sector and income band, and inflate "
                    "responding weights by the reciprocal of each class response rate.",
                    1.0,
                    "Correct. Weighting class adjustment is the standard treatment for "
                    "unit non-response, and these are exactly the variables known for "
                    "both respondents and non-respondents.",
                ),
                Option(
                    "impute",
                    "Impute expenditure values for the non-responding households.",
                    0.2,
                    "Imputation is for item non-response. These households supplied "
                    "nothing to predict from, so imputed values would be manufactured "
                    "rather than inferred.",
                ),
                Option(
                    "single",
                    "Apply one overall adjustment factor across the whole sample.",
                    0.4,
                    "A single factor corrects the total but not the composition. The "
                    "under-representation is concentrated in specific classes, and an "
                    "overall factor leaves that distortion in place.",
                ),
                Option(
                    "drop",
                    "Drop the affected blocks from the published estimates.",
                    0.1,
                    "This changes the target population without saying so, which is a "
                    "more serious problem than the one being avoided.",
                ),
            ],
        ),
        Decision(
            key="small_class",
            prompt=(
                "One weighting class contains only 11 responding households. What do "
                "you do?"
            ),
            context="Your guidance sets a minimum of 20 responding units per class.",
            weight=1.0,
            options=[
                Option(
                    "collapse",
                    "Collapse it with an adjacent class that is similar on the class "
                    "variables, and document the collapse.",
                    1.0,
                    "Correct. Small classes produce unstable adjustment factors. "
                    "Collapsing with a similar class preserves the adjustment's logic, "
                    "and documenting it keeps the process reproducible.",
                ),
                Option(
                    "proceed",
                    "Proceed with the class as it stands.",
                    0.1,
                    "Eleven units below a threshold of twenty will produce a volatile "
                    "factor that can swing the published estimate.",
                ),
                Option(
                    "trim",
                    "Proceed, then trim any extreme weights that result.",
                    0.5,
                    "Trimming controls the symptom. It is a legitimate safeguard, but "
                    "applied here it masks an unstable factor instead of fixing it.",
                ),
            ],
        ),
        Decision(
            key="document",
            prompt="What must appear in the methodology note?",
            context="The note accompanies the published estimates.",
            weight=1.0,
            options=[
                Option(
                    "assumption",
                    "The response rates by class, the adjustment applied, and an explicit "
                    "statement of the missing-at-random assumption being relied on.",
                    1.0,
                    "Correct. The adjustment rests on an assumption, not a finding. "
                    "Stating it lets a reader judge the estimate rather than take it on "
                    "trust.",
                ),
                Option(
                    "rate_only",
                    "The overall response rate.",
                    0.3,
                    "Necessary but not sufficient. It tells a reader nothing about what "
                    "you did in response.",
                ),
                Option(
                    "nothing",
                    "Nothing specific; weighting is routine practice.",
                    0.0,
                    "An undocumented adjustment cannot be reproduced or audited.",
                ),
            ],
        ),
    ],
)


ADMIN_DATA = Scenario(
    code="SIM-ADMIN",
    title="Administrative data inconsistency before publication",
    summary=(
        "An administrative register disagrees with survey estimates days before "
        "release. Decide how to reconcile and what to publish."
    ),
    briefing=(
        "A sample district's administrative register reports 12,400 registered "
        "enterprises. Your survey-based estimate is 9,100, with a 95 percent "
        "confidence interval of 8,600 to 9,600. The register counts registrations "
        "since 2015 and has no closure field. Publication is in five days."
    ),
    competency_code="COMP-ADMIN",
    estimated_minutes=5,
    decisions=[
        Decision(
            key="first_step",
            prompt="What do you investigate first?",
            context="Both sources are internally consistent with their own definitions.",
            weight=1.3,
            options=[
                Option(
                    "definitions",
                    "Compare the unit definitions and reference periods of the two "
                    "sources.",
                    1.0,
                    "Correct. A register counting cumulative registrations without "
                    "closures measures a different population from a survey of currently "
                    "active enterprises. This is a definitional gap before it is a data "
                    "quality problem.",
                ),
                Option(
                    "trust_register",
                    "Treat the register as authoritative, since it is a full count.",
                    0.2,
                    "Completeness of coverage is not the same as measuring the intended "
                    "concept. A full count of the wrong population is still wrong.",
                ),
                Option(
                    "average",
                    "Publish the midpoint of the two figures.",
                    0.0,
                    "Averaging two measurements of different concepts produces a number "
                    "that measures neither.",
                ),
                Option(
                    "resample",
                    "Commission a fresh survey round.",
                    0.3,
                    "Not wrong in principle, but it cannot be done in five days and would "
                    "not resolve a definitional difference.",
                ),
            ],
        ),
        Decision(
            key="explains",
            prompt=(
                "The register has no closure field, and roughly a quarter of "
                "registrations predate 2018. Does this explain the gap?"
            ),
            context="The gap is about 3,300 enterprises, or 36 percent above your estimate.",
            weight=1.2,
            options=[
                Option(
                    "plausible",
                    "It plausibly explains much of it; quantify the overlap before "
                    "concluding.",
                    1.0,
                    "Correct. Accumulated closures are a strong candidate explanation of "
                    "the right order of magnitude, but 'plausible' becomes 'established' "
                    "only after linking or matching quantifies it.",
                ),
                Option(
                    "fully",
                    "It fully explains it; no further work is needed.",
                    0.4,
                    "The direction is right but the conclusion outruns the evidence. You "
                    "have a hypothesis, not a measurement.",
                ),
                Option(
                    "unrelated",
                    "It is unrelated; the survey must be underestimating.",
                    0.1,
                    "This dismisses the most likely explanation in favour of assuming your "
                    "own estimate is at fault.",
                ),
            ],
        ),
        Decision(
            key="publish",
            prompt="What do you publish?",
            context="You cannot complete a full record linkage in five days.",
            weight=1.4,
            options=[
                Option(
                    "survey_with_note",
                    "Publish the survey estimate, with a note explaining the register "
                    "difference and its likely definitional cause.",
                    1.0,
                    "Correct. The survey measures the intended concept. Explaining the "
                    "discrepancy pre-empts it being discovered and misread as an error.",
                ),
                Option(
                    "survey_silent",
                    "Publish the survey estimate without reference to the register.",
                    0.4,
                    "Defensible on the number, weak on transparency. A user who knows both "
                    "sources will read the silence as an unexplained contradiction.",
                ),
                Option(
                    "delay",
                    "Delay publication until the linkage is complete.",
                    0.5,
                    "Cautious and not unreasonable, but the survey estimate is sound for "
                    "its stated concept; delay imposes a real cost to avoid a manageable "
                    "explanatory burden.",
                ),
                Option(
                    "register",
                    "Publish the register figure instead.",
                    0.0,
                    "This substitutes a number measuring a different population for the "
                    "one you set out to measure.",
                ),
            ],
        ),
    ],
)


SAMPLING_DESIGN = Scenario(
    code="SIM-SAMP",
    title="Choosing a sampling design under a fixed budget",
    summary=(
        "Design a sample for a district-level enterprise survey where a small "
        "stratum needs its own reliable estimate."
    ),
    briefing=(
        "You must design a sample of 2,000 enterprises across a sample state. "
        "Large enterprises are 3 percent of the frame but contribute most of the "
        "turnover, and the ministry has asked for a separate reliable estimate for "
        "them. Turnover is highly skewed and enterprise size class is on the frame."
    ),
    competency_code="COMP-SAMP",
    estimated_minutes=6,
    decisions=[
        Decision(
            key="design",
            prompt="Which design do you choose?",
            context="Size class is known for every unit on the frame.",
            weight=1.3,
            options=[
                Option(
                    "stratified",
                    "Stratify by size class and sample independently within each stratum.",
                    1.0,
                    "Correct. Size class is on the frame and is strongly related to "
                    "turnover, which is exactly when stratification reduces variance. It "
                    "also lets you control the sample size in the large-enterprise stratum "
                    "directly.",
                ),
                Option(
                    "srs",
                    "Simple random sampling across the whole frame.",
                    0.2,
                    "With large enterprises at 3 percent of the frame, an unstratified "
                    "sample would yield roughly 60 of them by chance alone - too few for a "
                    "reliable separate estimate, and it wastes the size information you "
                    "already hold.",
                ),
                Option(
                    "cluster",
                    "Cluster sampling by administrative block.",
                    0.3,
                    "Clustering saves field cost but raises variance for a skewed variable, "
                    "and does not guarantee coverage of the large enterprises.",
                ),
                Option(
                    "quota",
                    "Quota sampling on size class.",
                    0.0,
                    "Quota selection has no known selection probabilities, so no "
                    "design-consistent estimate or valid measure of precision can be "
                    "produced.",
                ),
            ],
        ),
        Decision(
            key="allocation",
            prompt="How do you allocate the 2,000 units across strata?",
            context=(
                "Turnover variance is far higher in the large-enterprise stratum, which "
                "also needs its own reliable estimate."
            ),
            weight=1.3,
            options=[
                Option(
                    "disproportionate",
                    "Oversample the large-enterprise stratum relative to its share, and "
                    "correct with weights at estimation.",
                    1.0,
                    "Correct. A separate reliable estimate for a small stratum requires "
                    "disproportionate allocation. It is legitimate precisely because the "
                    "weights restore unbiasedness at the estimation stage.",
                ),
                Option(
                    "neyman",
                    "Neyman allocation, in proportion to stratum size times standard "
                    "deviation.",
                    0.8,
                    "Strong reasoning: Neyman minimises variance of the overall estimate "
                    "for a fixed sample size, and will already favour the high-variance "
                    "stratum. It optimises the total, though, so it does not by itself "
                    "guarantee the separate estimate the ministry asked for.",
                ),
                Option(
                    "proportional",
                    "Proportional allocation, keeping the design self-weighting.",
                    0.4,
                    "Operationally convenient, but it returns you to roughly 60 large "
                    "enterprises - the problem stratification was meant to solve.",
                ),
                Option(
                    "equal",
                    "Equal allocation across strata.",
                    0.3,
                    "It guarantees a usable large-enterprise sample but badly over-samples "
                    "small strata, inflating the variance of state-level estimates.",
                ),
            ],
        ),
        Decision(
            key="estimation",
            prompt="What must happen at estimation because of this design?",
            context="You oversampled one stratum deliberately.",
            weight=1.2,
            options=[
                Option(
                    "weights",
                    "Apply design weights equal to the reciprocal of each unit's selection "
                    "probability.",
                    1.0,
                    "Correct. Disproportionate allocation is only valid if the differing "
                    "selection probabilities are undone by weighting. Without it, published "
                    "totals are biased toward the oversampled stratum.",
                ),
                Option(
                    "unweighted",
                    "Nothing special; compute unweighted means.",
                    0.0,
                    "This is the specific failure disproportionate allocation invites: "
                    "large enterprises would dominate the state average purely because you "
                    "selected more of them.",
                ),
                Option(
                    "trim_only",
                    "Trim extreme weights, but otherwise use unweighted estimates.",
                    0.2,
                    "Trimming is a variance safeguard applied to weights that are being "
                    "used. It is not a substitute for weighting.",
                ),
            ],
        ),
    ],
)


SCENARIOS: list[Scenario] = [NON_RESPONSE, ADMIN_DATA, SAMPLING_DESIGN]


def get_scenario(code: str) -> Scenario | None:
    return next((scenario for scenario in SCENARIOS if scenario.code == code), None)
