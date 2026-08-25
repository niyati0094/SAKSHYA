"""Document and generated-question contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filename: str
    content_type: str
    byte_size: int
    page_count: int
    chunk_count: int
    status: str
    error_message: str | None
    uploaded_at: datetime
    is_prototype_data: bool


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence: int
    page_number: int | None
    section_title: str | None
    content: str
    char_count: int


class SearchHitOut(BaseModel):
    chunk: ChunkOut
    score: float


class CitationOut(BaseModel):
    """Where a question came from. Always points at a stored chunk."""

    document_id: int
    document_title: str
    chunk_id: int
    page_number: int | None
    section_title: str | None
    quote: str


class GeneratedQuestionOut(BaseModel):
    id: int
    stem: str
    options: list[str]
    correct_index: int
    explanation: str

    citation: CitationOut
    grounding_status: str
    grounding_score: float
    grounding_note: str | None
    failed_gate: str | None
    failed_gate_name: str | None

    competency_id: int | None
    competency_name: str | None
    competency_tag_score: float | None

    review_status: str
    review_note: str | None
    reviewed_at: datetime | None
    edited: bool

    generator: str
    generation_strategy: str | None
    is_prototype_data: bool


class ReviewSummaryOut(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    ungrounded: int
    untagged: int
    #: Rejection rate across all generated items. A pipeline that never
    #: rejects anything is not verifying anything.
    rejection_rate: float
    #: How many items each gate rejected, keyed "G1".."G5".
    rejections_by_gate: dict[str, int]
    gate_names: dict[str, str]


class QuestionReviewRequest(BaseModel):
    """An SME decision, optionally carrying edits.

    Any edit triggers re-verification of grounding against the cited chunk.
    """

    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = None

    stem: str | None = None
    options: list[str] | None = None
    correct_index: int | None = None
    explanation: str | None = None
    competency_id: int | None = None


class GenerateRequest(BaseModel):
    max_questions: int = Field(default=8, ge=1, le=40)


class GateCheckRequest(BaseModel):
    """Run the verification gates against an arbitrary candidate item.

    Nothing is stored. This exists so a reviewer can test the pipeline against a
    known-bad item and watch which gate catches it.
    """

    passage: str = Field(min_length=20, max_length=4000)
    stem: str = Field(min_length=5, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=8)
    correct_index: int = Field(ge=0)
    source_quote: str | None = None


class GateOutcomeOut(BaseModel):
    gate: str
    name: str
    passed: bool
    note: str | None


class GateCheckOut(BaseModel):
    passed: bool
    failed_gate: str | None
    failed_gate_name: str | None
    note: str | None
    outcomes: list[GateOutcomeOut]
