"""Evidence records - the audit trail behind every competency claim."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.competency import Competency


class EvidenceType(str, enum.Enum):
    """Kinds of evidence, ordered by how strongly they demonstrate capability.

    Weights live in `app.engines.constants.EVIDENCE_TYPE_WEIGHTS`.
    COURSE_COMPLETION is deliberately the weakest: attendance is not capability.
    """

    SIMULATION = "simulation"
    PRACTICAL_SUBMISSION = "practical_submission"
    SME_VERIFIED = "sme_verified"
    ASSESSMENT = "assessment"
    PEER_REVIEW = "peer_review"
    COURSE_COMPLETION = "course_completion"


class ReviewStatus(str, enum.Enum):
    """Only ACCEPTED evidence contributes to a competency estimate.

    Pending and rejected evidence stays visible in the ledger - it is part of
    the audit trail - but does not move the number.
    """

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id", ondelete="CASCADE"), index=True, nullable=False
    )

    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType), nullable=False)

    #: What the learner actually did.
    activity_title: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Where it came from (assessment name, simulation scenario, catalogue item).
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    #: Set only when an expert overrides the default weight for this type.
    weight_override: Mapped[float | None] = mapped_column(Float, nullable=True)

    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.ACCEPTED, nullable=False, index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    is_prototype_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    competency: Mapped[Competency] = relationship()

    @property
    def normalized_score(self) -> float:
        """Score as 0..1, so the engine never deals with differing maximums."""
        if self.max_score <= 0:
            return 0.0
        return max(0.0, min(1.0, self.raw_score / self.max_score))

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Evidence {self.id} {self.evidence_type.value} score={self.normalized_score:.2f}>"
