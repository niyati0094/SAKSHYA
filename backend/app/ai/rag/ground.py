"""Grounding verification.

A generated question claims that its answer comes from a specific chunk. This
module checks that claim against the stored chunk text rather than trusting
the generator. An item that fails is flagged UNGROUNDED and held for human
review; it is never silently published as sourced.

This is what makes "the system must not invent source citations" enforceable
rather than aspirational: the citation points at a stored row, and the quote
is verified against that row's text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.question import GroundingStatus

#: Token-containment score at or above which a quote counts as present. Below
#: 1.0 so that whitespace, hyphenation and quote-character differences do not
#: fail an otherwise verbatim match.
GROUNDING_THRESHOLD = 0.92

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class GroundingResult:
    status: GroundingStatus
    score: float
    note: str | None

    @property
    def is_grounded(self) -> bool:
        return self.status is GroundingStatus.GROUNDED


def _normalise(text: str) -> str:
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(_normalise(text))


def verify_quote(quote: str, chunk_text: str) -> GroundingResult:
    """Check that `quote` genuinely appears in `chunk_text`."""
    if not quote.strip():
        return GroundingResult(
            GroundingStatus.UNGROUNDED, 0.0, "No source quote was supplied."
        )

    normalised_quote = _normalise(quote)
    normalised_chunk = _normalise(chunk_text)

    if normalised_quote in normalised_chunk:
        return GroundingResult(GroundingStatus.GROUNDED, 1.0, None)

    # Fall back to token containment, which tolerates punctuation and layout
    # differences introduced by PDF extraction.
    quote_tokens = _tokens(quote)
    if not quote_tokens:
        return GroundingResult(
            GroundingStatus.UNGROUNDED, 0.0, "The source quote contains no words."
        )

    chunk_tokens = set(_tokens(chunk_text))
    present = sum(1 for token in quote_tokens if token in chunk_tokens)
    score = present / len(quote_tokens)

    if score >= GROUNDING_THRESHOLD:
        return GroundingResult(GroundingStatus.GROUNDED, round(score, 4), None)

    return GroundingResult(
        GroundingStatus.UNGROUNDED,
        round(score, 4),
        (
            f"Only {score:.0%} of the quoted text was found in the cited passage "
            f"(threshold {GROUNDING_THRESHOLD:.0%}). The citation could not be "
            "verified, so this question needs expert review before use."
        ),
    )


def verify_question(
    *, source_quote: str, correct_option: str, chunk_text: str
) -> GroundingResult:
    """Verify both the quote and that the correct answer is supported by it.

    Two claims are checked: that the cited passage really contains the quote,
    and that the answer being marked correct actually appears in that passage.
    A question can cite real text and still mark an answer the text does not
    support - that is caught here.
    """
    quote_result = verify_quote(source_quote, chunk_text)
    if not quote_result.is_grounded:
        return quote_result

    answer_result = verify_quote(correct_option, chunk_text)
    if not answer_result.is_grounded:
        return GroundingResult(
            GroundingStatus.UNGROUNDED,
            answer_result.score,
            (
                "The cited passage was verified, but the answer marked correct "
                "was not found in it. This question needs expert review."
            ),
        )

    return GroundingResult(
        GroundingStatus.GROUNDED,
        round(min(quote_result.score, answer_result.score), 4),
        None,
    )
