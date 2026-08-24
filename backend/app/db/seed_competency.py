"""Prototype competency framework and demo evidence.

PROTOTYPE SAMPLE DATA. The role, competencies and target levels below are
illustrative constructs written for this hackathon prototype. They are NOT an
official Government of India competency framework, and no official mapping is
reproduced or implied. Every row is flagged `is_prototype_data=True`.

The demo learner's evidence is deliberately shaped so the dashboard shows the
full range of honest outcomes:

  * a competency below target, with a real gap        (Sampling Design)
  * competencies meeting target with solid evidence   (Questionnaire, DQA, SDC)
  * a competency with only a course completion, which
    the engine refuses to accept as proof             (Non-Response Analysis)
  * a competency whose only evidence is unreviewed,
    so it does not count at all                       (Admin Data Integration)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competency import (
    Competency,
    Criticality,
    LearnerProfile,
    RoleCompetency,
    StatisticalRole,
)
from app.models.evidence import Evidence, EvidenceType, ReviewStatus
from app.models.user import User

DEMO_ROLE_CODE = "JSO-PROTO"

COMPETENCIES: list[dict] = [
    {
        "code": "COMP-SAMP",
        "name": "Sampling Design & Estimation",
        "domain": "Survey Methodology",
        "description": (
            "Selecting appropriate sampling designs, computing selection "
            "probabilities, and producing design-consistent estimates with "
            "measures of precision."
        ),
        "target_level": 3,
        "criticality": Criticality.CRITICAL,
    },
    {
        "code": "COMP-QDES",
        "name": "Questionnaire Design",
        "domain": "Survey Methodology",
        "description": (
            "Constructing survey instruments with unambiguous wording, "
            "appropriate response formats and tested respondent flow."
        ),
        "target_level": 2,
        "criticality": Criticality.HIGH,
    },
    {
        "code": "COMP-DQA",
        "name": "Data Quality Assurance & Editing",
        "domain": "Data Processing",
        "description": (
            "Applying validation rules, detecting and treating outliers, and "
            "documenting editing decisions so results remain reproducible."
        ),
        "target_level": 3,
        "criticality": Criticality.CRITICAL,
    },
    {
        "code": "COMP-NRES",
        "name": "Non-Response Analysis & Adjustment",
        "domain": "Survey Methodology",
        "description": (
            "Diagnosing unit and item non-response, assessing bias risk, and "
            "applying weighting or imputation adjustments defensibly."
        ),
        "target_level": 3,
        "criticality": Criticality.CRITICAL,
    },
    {
        "code": "COMP-ADMIN",
        "name": "Administrative Data Integration",
        "domain": "Data Sources",
        "description": (
            "Reconciling administrative registers with survey data, resolving "
            "definitional differences and documenting inconsistencies before "
            "publication."
        ),
        "target_level": 2,
        "criticality": Criticality.MEDIUM,
    },
    {
        "code": "COMP-SDC",
        "name": "Statistical Disclosure Control",
        "domain": "Dissemination",
        "description": (
            "Assessing re-identification risk and applying suppression or "
            "perturbation so published tables protect respondent confidentiality."
        ),
        "target_level": 2,
        "criticality": Criticality.HIGH,
    },
]

# (competency code, evidence type, raw score, max score, days ago, review status,
#  activity title, source, notes)
DEMO_EVIDENCE: list[tuple] = [
    # --- Sampling Design: below target. Two assessments, one evidence type only.
    (
        "COMP-SAMP",
        EvidenceType.ASSESSMENT,
        11.0,
        20.0,
        200,
        ReviewStatus.ACCEPTED,
        "Sampling frames and selection probabilities — diagnostic quiz",
        "SAKSHYA assessment (prototype)",
        None,
    ),
    (
        "COMP-SAMP",
        EvidenceType.ASSESSMENT,
        12.0,
        25.0,
        60,
        ReviewStatus.ACCEPTED,
        "Stratification and estimator choice — assessment",
        "SAKSHYA assessment (prototype)",
        "Errors concentrated on variance estimation for stratified designs.",
    ),
    # --- Questionnaire Design: meets target, three evidence types.
    (
        "COMP-QDES",
        EvidenceType.ASSESSMENT,
        18.0,
        25.0,
        90,
        ReviewStatus.ACCEPTED,
        "Question wording and response formats — assessment",
        "SAKSHYA assessment (prototype)",
        None,
    ),
    (
        "COMP-QDES",
        EvidenceType.SIMULATION,
        15.0,
        20.0,
        45,
        ReviewStatus.ACCEPTED,
        "Household schedule redesign — simulation",
        "SAKSHYA simulation lab (prototype)",
        "Correctly identified double-barrelled items and fixed the skip logic.",
    ),
    (
        "COMP-QDES",
        EvidenceType.COURSE_COMPLETION,
        85.0,
        100.0,
        120,
        ReviewStatus.ACCEPTED,
        "Designing Survey Instruments — course completed",
        "Local prototype learning catalogue",
        None,
    ),
    # --- Data Quality Assurance: meets target.
    (
        "COMP-DQA",
        EvidenceType.ASSESSMENT,
        17.0,
        25.0,
        30,
        ReviewStatus.ACCEPTED,
        "Edit rules and outlier treatment — assessment",
        "SAKSHYA assessment (prototype)",
        None,
    ),
    (
        "COMP-DQA",
        EvidenceType.PRACTICAL_SUBMISSION,
        37.0,
        50.0,
        75,
        ReviewStatus.ACCEPTED,
        "Editing rule set for a price collection dataset — reviewed submission",
        "SME-reviewed submission (prototype)",
        "Reviewed by SME. Sound rules; documentation of overrides was thin.",
    ),
    # --- Non-Response Analysis: a high course score that is NOT proof.
    (
        "COMP-NRES",
        EvidenceType.COURSE_COMPLETION,
        95.0,
        100.0,
        40,
        ReviewStatus.ACCEPTED,
        "Handling Non-Response in Household Surveys — course completed",
        "Local prototype learning catalogue",
        "Course completed with a high mark, but capability has not been "
        "demonstrated in an assessment or simulation.",
    ),
    # --- Administrative Data Integration: sole evidence awaits review.
    (
        "COMP-ADMIN",
        EvidenceType.PRACTICAL_SUBMISSION,
        40.0,
        50.0,
        10,
        ReviewStatus.PENDING,
        "Register-to-survey reconciliation note — submitted for review",
        "SME review queue (prototype)",
        "Awaiting subject matter expert review.",
    ),
    # --- Statistical Disclosure Control: meets target.
    (
        "COMP-SDC",
        EvidenceType.ASSESSMENT,
        16.5,
        25.0,
        15,
        ReviewStatus.ACCEPTED,
        "Disclosure risk and suppression rules — assessment",
        "SAKSHYA assessment (prototype)",
        None,
    ),
    (
        "COMP-SDC",
        EvidenceType.SME_VERIFIED,
        14.0,
        20.0,
        100,
        ReviewStatus.ACCEPTED,
        "Table suppression review — expert-verified observation",
        "SME verification (prototype)",
        "Observed applying primary and secondary suppression correctly.",
    ),
]


def seed_framework(db: Session) -> tuple[StatisticalRole, dict[str, Competency]]:
    """Create the prototype role, competencies and role mapping. Idempotent."""
    role = db.scalar(select(StatisticalRole).where(StatisticalRole.code == DEMO_ROLE_CODE))
    if role is None:
        role = StatisticalRole(
            code=DEMO_ROLE_CODE,
            name="Junior Statistical Officer (prototype sample role)",
            description=(
                "Illustrative sample role used to demonstrate SAKSHYA. Not an "
                "official Government of India role definition."
            ),
            is_prototype_data=True,
        )
        db.add(role)
        db.flush()

    competencies: dict[str, Competency] = {}
    for spec in COMPETENCIES:
        competency = db.scalar(select(Competency).where(Competency.code == spec["code"]))
        if competency is None:
            competency = Competency(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                domain=spec["domain"],
                is_prototype_data=True,
            )
            db.add(competency)
            db.flush()
        competencies[spec["code"]] = competency

        link = db.scalar(
            select(RoleCompetency).where(
                RoleCompetency.role_id == role.id,
                RoleCompetency.competency_id == competency.id,
            )
        )
        if link is None:
            db.add(
                RoleCompetency(
                    role_id=role.id,
                    competency_id=competency.id,
                    target_level=spec["target_level"],
                    criticality=spec["criticality"],
                    sequence=COMPETENCIES.index(spec),
                )
            )

    db.commit()
    return role, competencies


def seed_learner_evidence(db: Session, learner: User) -> int:
    """Attach the demo learner to the prototype role and seed their evidence.

    Returns the number of evidence rows created. Idempotent: if the learner
    already has evidence, nothing is added.
    """
    role, competencies = seed_framework(db)

    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == learner.id))
    if profile is None:
        db.add(
            LearnerProfile(
                user_id=learner.id,
                statistical_role_id=role.id,
                is_prototype_data=True,
            )
        )
        db.commit()

    existing = db.scalar(select(Evidence).where(Evidence.user_id == learner.id))
    if existing is not None:
        return 0

    now = datetime.now(timezone.utc)
    created = 0
    for (
        code,
        evidence_type,
        raw_score,
        max_score,
        days_ago,
        review_status,
        title,
        source,
        notes,
    ) in DEMO_EVIDENCE:
        db.add(
            Evidence(
                user_id=learner.id,
                competency_id=competencies[code].id,
                evidence_type=evidence_type,
                activity_title=title,
                source=source,
                raw_score=raw_score,
                max_score=max_score,
                review_status=review_status,
                reviewed_by=(
                    "Dr. Vikram Iyer (prototype SME)"
                    if review_status is ReviewStatus.ACCEPTED
                    and evidence_type
                    in {EvidenceType.PRACTICAL_SUBMISSION, EvidenceType.SME_VERIFIED}
                    else None
                ),
                notes=notes,
                observed_at=now - timedelta(days=days_ago),
                is_prototype_data=True,
            )
        )
        created += 1

    db.commit()
    return created
