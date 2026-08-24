"""AI-drafted assessment questions and their human review state."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.competency import Competency
from app.models.document import Document, DocumentChunk


class GroundingStatus(str, enum.Enum):
    """Whether the question's answer was found in its cited source text.

    A question is never published as grounded on the generator's say-so; the
    quote is checked against the cited chunk after generation.
    """

    GROUNDED = "grounded"
    UNGROUNDED = "ungrounded"


class QuestionReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GeneratedQuestion(Base):
    __tablename__ = "generated_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: The chunk this question is cited to. Citations point at stored text, so
    #: they cannot be fabricated.
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True, nullable=False
    )

    stem: Mapped[str] = mapped_column(Text, nullable=False)
    #: JSON-encoded list of option strings.
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    #: Verbatim sentence the answer was taken from.
    source_quote: Mapped[str] = mapped_column(Text, nullable=False)

    grounding_status: Mapped[GroundingStatus] = mapped_column(
        Enum(GroundingStatus), nullable=False, index=True
    )
    grounding_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    grounding_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Suggested by similarity, confirmed by an SME. Nullable: an untagged
    #: question is surfaced for tagging rather than guessed at.
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    competency_tag_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    review_status: Mapped[QuestionReviewStatus] = mapped_column(
        Enum(QuestionReviewStatus),
        default=QuestionReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: True once an SME has changed the wording or options.
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    generator: Mapped[str] = mapped_column(String(128), nullable=False)
    generation_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_prototype_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    document: Mapped[Document] = relationship()
    chunk: Mapped[DocumentChunk] = relationship()
    competency: Mapped[Competency | None] = relationship()
