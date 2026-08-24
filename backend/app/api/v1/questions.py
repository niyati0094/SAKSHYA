"""Generated questions and the subject-matter-expert review queue."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.question import GeneratedQuestion, QuestionReviewStatus
from app.models.user import User, UserRole
from app.schemas.document import (
    CitationOut,
    GeneratedQuestionOut,
    GenerateRequest,
    QuestionReviewRequest,
    ReviewSummaryOut,
)
from app.services import document_service, question_service

router = APIRouter(tags=["questions"])

require_content_manager = require_roles(UserRole.SME, UserRole.ADMIN)
require_reviewer = require_roles(UserRole.SME)


def _to_out(question: GeneratedQuestion) -> GeneratedQuestionOut:
    return GeneratedQuestionOut(
        id=question.id,
        stem=question.stem,
        options=json.loads(question.options_json),
        correct_index=question.correct_index,
        explanation=question.explanation,
        citation=CitationOut(
            document_id=question.document_id,
            document_title=question.document.title,
            chunk_id=question.chunk_id,
            page_number=question.chunk.page_number,
            section_title=question.chunk.section_title,
            quote=question.source_quote,
        ),
        grounding_status=question.grounding_status.value,
        grounding_score=question.grounding_score,
        grounding_note=question.grounding_note,
        competency_id=question.competency_id,
        competency_name=question.competency.name if question.competency else None,
        competency_tag_score=question.competency_tag_score,
        review_status=question.review_status.value,
        review_note=question.review_note,
        reviewed_at=question.reviewed_at,
        edited=question.edited,
        generator=question.generator,
        generation_strategy=question.generation_strategy,
        is_prototype_data=question.is_prototype_data,
    )


@router.post(
    "/documents/{document_id}/generate-questions",
    response_model=list[GeneratedQuestionOut],
    status_code=status.HTTP_201_CREATED,
)
def generate_questions(
    document_id: int,
    payload: GenerateRequest | None = None,
    _: User = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> list[GeneratedQuestionOut]:
    """Draft questions from a document, verifying each against its own source.

    Ungrounded items are returned flagged rather than discarded, so a
    generation failure is visible to a reviewer instead of silently dropped.
    """
    document = document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    created = question_service.generate_for_document(
        db, document_id, max_questions=(payload.max_questions if payload else 8)
    )
    return [_to_out(question) for question in created]


@router.get("/questions", response_model=list[GeneratedQuestionOut])
def list_questions(
    document_id: int | None = Query(default=None),
    review_status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeneratedQuestionOut]:
    """List questions.

    Learners only ever see approved items: an unreviewed or rejected question
    must not reach an assessment.
    """
    status_filter: QuestionReviewStatus | None = None

    if current_user.role is UserRole.LEARNER:
        status_filter = QuestionReviewStatus.APPROVED
    elif review_status:
        try:
            status_filter = QuestionReviewStatus(review_status)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown review status '{review_status}'. Expected one of: "
                    + ", ".join(item.value for item in QuestionReviewStatus)
                ),
            ) from exc

    questions = question_service.list_questions(
        db, document_id=document_id, review_status=status_filter
    )
    return [_to_out(question) for question in questions]


@router.get("/questions/summary", response_model=ReviewSummaryOut)
def summary(
    _: User = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> ReviewSummaryOut:
    return ReviewSummaryOut(**question_service.review_summary(db))


@router.post("/questions/{question_id}/review", response_model=GeneratedQuestionOut)
def review_question(
    question_id: int,
    payload: QuestionReviewRequest,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> GeneratedQuestionOut:
    """Approve or reject a question, optionally editing it first."""
    question = question_service.get_question(db, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    try:
        updated = question_service.review_question(
            db,
            question,
            reviewer_id=current_user.id,
            decision=QuestionReviewStatus(payload.decision),
            note=payload.note,
            stem=payload.stem,
            options=payload.options,
            correct_index=payload.correct_index,
            explanation=payload.explanation,
            competency_id=payload.competency_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return _to_out(updated)
