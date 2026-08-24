"""Seed the synthetic learning material and its generated questions.

The shipped document is synthetic material written for this prototype (see the
disclaimer inside it). It is ingested through the same pipeline a user upload
takes - extract, chunk, embed - so the seeded state is genuinely the product of
the pipeline rather than hand-written fixtures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.question import GeneratedQuestion, QuestionReviewStatus
from app.models.user import User, UserRole
from app.services import document_service, question_service

SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent / "ai" / "sample_material"
    / "sampling_and_nonresponse.md"
)
SAMPLE_TITLE = "Foundations of Survey Sampling and Non-Response Adjustment (synthetic)"


def seed_sample_document(db: Session, uploader: User | None) -> tuple[int, int]:
    """Ingest the sample document and generate questions.

    Returns (documents_created, questions_created). Idempotent.
    """
    existing = db.scalar(select(Document).where(Document.title == SAMPLE_TITLE))
    if existing is not None:
        return 0, 0

    if not SAMPLE_PATH.exists():  # pragma: no cover - packaging guard
        return 0, 0

    document = document_service.ingest_document(
        db,
        title=SAMPLE_TITLE,
        filename=SAMPLE_PATH.name,
        content_type="text/markdown",
        data=SAMPLE_PATH.read_bytes(),
        uploaded_by_id=uploader.id if uploader else None,
        is_prototype_data=True,
    )

    questions = question_service.generate_for_document(db, document.id, max_questions=8)
    _seed_review_decisions(db, questions, uploader)
    return 1, len(questions)


def _seed_review_decisions(
    db: Session, questions: list[GeneratedQuestion], reviewer: User | None
) -> None:
    """Pre-review some questions so the SME queue shows a realistic mix.

    Decisions are made by content, not by position: anything drawn from the
    document's front matter is rejected the way a real reviewer would reject
    it, two solid technical items are approved, and the rest stay pending so
    the demo has live items to act on.
    """
    if reviewer is None or reviewer.role is not UserRole.SME:
        return

    now = datetime.now(timezone.utc)
    approved = 0

    for question in questions:
        section = question.chunk.section_title or ""
        # Numbered sections are the technical body; anything else is front
        # matter (title block, synthetic-material disclaimer).
        is_front_matter = not section[:1].isdigit()

        if is_front_matter:
            question.review_status = QuestionReviewStatus.REJECTED
            question.review_note = (
                "Drawn from the document's front matter rather than its technical "
                "content; not suitable as an assessment item."
            )
        elif approved < 2:
            question.review_status = QuestionReviewStatus.APPROVED
            question.review_note = "Wording is clear and the citation checks out."
            approved += 1
        else:
            continue

        question.reviewed_by_id = reviewer.id
        question.reviewed_at = now

    db.commit()
