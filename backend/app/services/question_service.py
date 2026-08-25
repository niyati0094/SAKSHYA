"""Question generation and subject-matter-expert review."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.providers import get_embedding_provider, get_llm_provider
from app.ai.rag.gates import GATE_NAMES, verify_item
from app.ai.rag.tag import suggest_competency, tagging_text
from app.models.competency import Competency
from app.models.document import DocumentChunk
from app.models.question import (
    GeneratedQuestion,
    GroundingStatus,
    QuestionReviewStatus,
)


def _competency_corpus(db: Session) -> list[tuple[int, str]]:
    competencies = db.scalars(select(Competency).order_by(Competency.id))
    return [
        (item.id, f"{item.name}. {item.domain or ''}. {item.description or ''}")
        for item in competencies
    ]


def generate_for_document(
    db: Session,
    document_id: int,
    *,
    max_questions: int = 8,
) -> list[GeneratedQuestion]:
    """Draft questions from a document's chunks, verify, tag, and store.

    Every question is verified against its own cited chunk before being saved.
    Ungrounded items are stored too - flagged, and held in the review queue -
    because hiding them would conceal the failure rather than surface it.
    """
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.sequence)
        )
    )
    if not chunks:
        return []

    # Existing questions are not regenerated, so repeated calls are safe.
    already = set(
        db.scalars(
            select(GeneratedQuestion.chunk_id).where(
                GeneratedQuestion.document_id == document_id
            )
        )
    )

    llm = get_llm_provider()
    embedder = get_embedding_provider()
    competencies = _competency_corpus(db)

    created: list[GeneratedQuestion] = []

    for chunk in chunks:
        if len(created) >= max_questions:
            break
        if chunk.id in already:
            continue

        # Distractors come from other chunks of the same document, so wrong
        # options are real sentences rather than invented ones.
        pool: list[str] = []
        for other in chunks:
            if other.id != chunk.id:
                pool.extend(_sentences(other.content))

        drafts = llm.draft_questions(
            chunk_text=chunk.content, distractor_pool=pool, max_questions=1
        )

        for draft in drafts:
            grounding = verify_item(
                stem=draft.stem,
                options=draft.options,
                correct_index=draft.correct_index,
                source_quote=draft.source_quote,
                chunk_text=chunk.content,
            )
            tag = suggest_competency(
                text=tagging_text(chunk.section_title, chunk.content),
                competencies=competencies,
                embedder=embedder,
            )

            question = GeneratedQuestion(
                document_id=document_id,
                chunk_id=chunk.id,
                stem=draft.stem,
                options_json=json.dumps(draft.options),
                correct_index=draft.correct_index,
                explanation=draft.explanation,
                source_quote=draft.source_quote,
                grounding_status=grounding.grounding_status,
                grounding_score=grounding.grounding_score,
                grounding_note=grounding.note,
                failed_gate=grounding.failed_gate,
                competency_id=tag.competency_id,
                competency_tag_score=tag.score,
                review_status=QuestionReviewStatus.PENDING,
                generator=llm.name,
                generation_strategy=draft.metadata.get("strategy"),
                is_prototype_data=True,
            )
            db.add(question)
            created.append(question)

    db.commit()
    for question in created:
        db.refresh(question)
    return created


def _sentences(text: str) -> list[str]:
    from app.ai.providers.mock import split_sentences

    return split_sentences(text)


def list_questions(
    db: Session,
    *,
    document_id: int | None = None,
    review_status: QuestionReviewStatus | None = None,
) -> list[GeneratedQuestion]:
    statement = (
        select(GeneratedQuestion)
        .options(
            selectinload(GeneratedQuestion.chunk),
            selectinload(GeneratedQuestion.document),
            selectinload(GeneratedQuestion.competency),
        )
        .order_by(GeneratedQuestion.id)
    )
    if document_id is not None:
        statement = statement.where(GeneratedQuestion.document_id == document_id)
    if review_status is not None:
        statement = statement.where(GeneratedQuestion.review_status == review_status)
    return list(db.scalars(statement))


def get_question(db: Session, question_id: int) -> GeneratedQuestion | None:
    return db.get(GeneratedQuestion, question_id)


def review_question(
    db: Session,
    question: GeneratedQuestion,
    *,
    reviewer_id: int,
    decision: QuestionReviewStatus,
    note: str | None = None,
    stem: str | None = None,
    options: list[str] | None = None,
    correct_index: int | None = None,
    explanation: str | None = None,
    competency_id: int | None = None,
) -> GeneratedQuestion:
    """Apply an SME decision, optionally with edits.

    Edited questions are re-verified against their cited chunk: an expert may
    correct wording, but the grounding claim is re-checked rather than assumed
    to survive the edit.
    """
    edited = False

    if stem is not None and stem.strip() and stem != question.stem:
        question.stem = stem.strip()
        edited = True

    if options is not None:
        cleaned = [option.strip() for option in options if option.strip()]
        if len(cleaned) < 2:
            raise ValueError("A question needs at least two options.")
        question.options_json = json.dumps(cleaned)
        edited = True
        # Keep correct_index inside the new option list.
        if correct_index is None and question.correct_index >= len(cleaned):
            question.correct_index = 0

    if correct_index is not None:
        current = json.loads(question.options_json)
        if not 0 <= correct_index < len(current):
            raise ValueError("correct_index is outside the option list.")
        question.correct_index = correct_index
        edited = True

    if explanation is not None and explanation.strip():
        question.explanation = explanation.strip()
        edited = True

    if competency_id is not None:
        question.competency_id = competency_id
        edited = True

    if edited:
        question.edited = True
        chunk = db.get(DocumentChunk, question.chunk_id)
        if chunk is not None:
            options_now = json.loads(question.options_json)
            grounding = verify_item(
                stem=question.stem,
                options=options_now,
                correct_index=question.correct_index,
                source_quote=question.source_quote,
                chunk_text=chunk.content,
            )
            question.grounding_status = grounding.grounding_status
            question.grounding_score = grounding.grounding_score
            question.grounding_note = grounding.note
            question.failed_gate = grounding.failed_gate

    question.review_status = decision
    question.reviewed_by_id = reviewer_id
    question.reviewed_at = datetime.now(timezone.utc)
    question.review_note = note

    db.commit()
    db.refresh(question)
    return question


def review_summary(db: Session) -> dict:
    questions = list(db.scalars(select(GeneratedQuestion)))
    return {
        "total": len(questions),
        "pending": sum(
            1 for q in questions if q.review_status is QuestionReviewStatus.PENDING
        ),
        "approved": sum(
            1 for q in questions if q.review_status is QuestionReviewStatus.APPROVED
        ),
        "rejected": sum(
            1 for q in questions if q.review_status is QuestionReviewStatus.REJECTED
        ),
        "ungrounded": sum(
            1 for q in questions if q.grounding_status is GroundingStatus.UNGROUNDED
        ),
        "untagged": sum(1 for q in questions if q.competency_id is None),
        "rejection_rate": (
            round(sum(1 for q in questions if q.failed_gate) / len(questions), 4)
            if questions
            else 0.0
        ),
        "rejections_by_gate": {
            gate: sum(1 for q in questions if q.failed_gate == gate)
            for gate in GATE_NAMES
        },
        "gate_names": dict(GATE_NAMES),
    }
