"""Extraction, chunking, embeddings, retrieval and grounding verification."""

import pytest

from app.ai.providers.mock import MockEmbeddingProvider, MockLLMProvider, split_sentences
from app.ai.rag.chunk import MAX_CHARS, chunk_pages
from app.ai.rag.extract import ExtractedPage, ExtractionError, detect_kind
from app.ai.rag.ground import GROUNDING_THRESHOLD, verify_question, verify_quote
from app.models.question import GroundingStatus

SAMPLE = """# Survey Methods

## 1. Sampling Frames

A sampling frame is the list or procedure that identifies every unit in the
target population. Undercoverage occurs when eligible units are absent from the
frame, so they have zero probability of selection and cannot be recovered by
weighting.

A frame with more than 5 percent undercoverage requires documented remedial
action before use in a production survey.

## 2. Imputation

Imputation replaces a missing item value with a constructed value so that
analysis can proceed. Hot-deck imputation copies a value from a similar
responding unit called the donor.
"""


@pytest.fixture
def chunks():
    return chunk_pages([ExtractedPage(page_number=None, text=SAMPLE)])


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,content_type,expected",
    [
        ("a.pdf", "application/pdf", "pdf"),
        ("a.pdf", None, "pdf"),
        ("notes.md", "text/markdown", "text"),
        ("notes.txt", None, "text"),
        ("notes.md", "application/octet-stream", "text"),
    ],
)
def test_detect_kind(filename, content_type, expected):
    assert detect_kind(filename, content_type) == expected


def test_unsupported_file_type_is_rejected_clearly():
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        detect_kind("virus.exe", "application/x-msdownload")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def test_chunking_preserves_section_headings(chunks):
    sections = {chunk.section_title for chunk in chunks}
    assert "1. Sampling Frames" in sections
    assert "2. Imputation" in sections


def test_chunks_respect_the_size_ceiling(chunks):
    assert all(len(chunk.content) <= MAX_CHARS for chunk in chunks)


def test_chunks_are_sequentially_numbered(chunks):
    assert [chunk.sequence for chunk in chunks] == list(range(len(chunks)))


def test_trivial_fragments_are_dropped():
    """Rule lines and stray punctuation must not become retrievable chunks."""
    produced = chunk_pages([ExtractedPage(page_number=None, text="---\n\n***\n\nx\n")])
    assert produced == []


def test_page_numbers_are_carried_through_for_citation():
    produced = chunk_pages(
        [
            ExtractedPage(page_number=1, text="Alpha " * 40),
            ExtractedPage(page_number=7, text="Beta " * 40),
        ]
    )
    assert {chunk.page_number for chunk in produced} == {1, 7}


# ---------------------------------------------------------------------------
# Embeddings and retrieval
# ---------------------------------------------------------------------------


def test_embeddings_are_deterministic():
    provider = MockEmbeddingProvider()
    assert provider.embed(["sampling frame"]) == provider.embed(["sampling frame"])


def test_embeddings_are_unit_length():
    vector = MockEmbeddingProvider().embed(["stratified sampling design"])[0]
    assert sum(value * value for value in vector) == pytest.approx(1.0, abs=1e-6)


def test_empty_text_does_not_crash_the_embedder():
    assert len(MockEmbeddingProvider().embed([""])[0]) == MockEmbeddingProvider().dimensions


def test_retrieval_ranks_the_relevant_passage_first(chunks):
    provider = MockEmbeddingProvider()
    vectors = provider.embed([chunk.content for chunk in chunks])
    query = provider.embed(["What is hot-deck imputation?"])[0]

    scores = [sum(a * b for a, b in zip(query, vector)) for vector in vectors]
    best = chunks[scores.index(max(scores))]

    assert "imputation" in best.content.lower()


# ---------------------------------------------------------------------------
# Grounding verification
# ---------------------------------------------------------------------------


def test_verbatim_quote_is_grounded():
    result = verify_quote("the donor", "copies a value from a similar unit called the donor.")
    assert result.status is GroundingStatus.GROUNDED
    assert result.score == 1.0


def test_invented_quote_is_flagged_not_accepted():
    """The central safeguard: a citation that is not in the source must fail."""
    result = verify_quote(
        "The survey achieved a 92 percent response rate in every district.",
        "Imputation replaces a missing item value with a constructed value.",
    )
    assert result.status is GroundingStatus.UNGROUNDED
    assert result.score < GROUNDING_THRESHOLD
    assert "could not be verified" in result.note


def test_whitespace_and_punctuation_differences_still_ground():
    result = verify_quote(
        "A  sampling   frame is the list", "A sampling frame is the list or procedure"
    )
    assert result.status is GroundingStatus.GROUNDED


def test_empty_quote_is_ungrounded():
    assert verify_quote("   ", "anything").status is GroundingStatus.UNGROUNDED


def test_correct_answer_absent_from_source_is_caught():
    """A real citation with an unsupported answer must not pass."""
    result = verify_question(
        source_quote="Imputation replaces a missing item value.",
        correct_option="Ninety-two percent of households responded.",
        chunk_text="Imputation replaces a missing item value with a constructed value.",
    )
    assert result.status is GroundingStatus.UNGROUNDED
    assert "answer marked correct was not found" in result.note


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------


def test_generated_questions_are_grounded_in_their_source(chunks):
    llm = MockLLMProvider()
    pool = [s for chunk in chunks for s in split_sentences(chunk.content)]

    produced = 0
    for chunk in chunks:
        for draft in llm.draft_questions(
            chunk_text=chunk.content, distractor_pool=pool, max_questions=1
        ):
            produced += 1
            result = verify_question(
                source_quote=draft.source_quote,
                correct_option=draft.correct_option,
                chunk_text=chunk.content,
            )
            assert result.status is GroundingStatus.GROUNDED, draft.stem

    assert produced > 0, "the generator must produce questions from this document"


def test_generation_is_deterministic(chunks):
    llm = MockLLMProvider()
    pool = [s for chunk in chunks for s in split_sentences(chunk.content)]
    args = {"chunk_text": chunks[0].content, "distractor_pool": pool, "max_questions": 2}

    first = llm.draft_questions(**args)
    second = llm.draft_questions(**args)

    assert [d.stem for d in first] == [d.stem for d in second]
    assert [d.options for d in first] == [d.options for d in second]


def test_options_are_distinct_and_answer_is_inside_range(chunks):
    llm = MockLLMProvider()
    pool = [s for chunk in chunks for s in split_sentences(chunk.content)]

    for chunk in chunks:
        for draft in llm.draft_questions(
            chunk_text=chunk.content, distractor_pool=pool, max_questions=1
        ):
            assert len(set(draft.options)) == len(draft.options), "duplicate options"
            assert 0 <= draft.correct_index < len(draft.options)
            assert len(draft.options) >= 3


def test_answer_is_not_always_in_the_same_position(chunks):
    """Option order is deterministic but must not leak the answer."""
    llm = MockLLMProvider()
    pool = [s for chunk in chunks for s in split_sentences(chunk.content)]

    positions = {
        draft.correct_index
        for chunk in chunks
        for draft in llm.draft_questions(
            chunk_text=chunk.content, distractor_pool=pool, max_questions=1
        )
    }
    assert len(positions) > 1, "the correct answer sits in the same slot every time"


def test_generator_produces_no_questions_from_contentless_text():
    llm = MockLLMProvider()
    assert llm.draft_questions(chunk_text="...", distractor_pool=[], max_questions=3) == []
