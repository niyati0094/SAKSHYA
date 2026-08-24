"""Provider-agnostic AI interfaces.

Two capabilities are abstracted: turning text into vectors, and drafting
question candidates from source text. Call sites depend only on these
protocols, so a real hosted model can replace the offline implementation
without touching the pipeline.

Nothing behind these interfaces is permitted to influence a competency score.
AI drafts content; `app.engines` decides numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class QuestionDraft:
    """A candidate multiple-choice question, before grounding verification.

    `source_quote` must be text lifted verbatim from the supplied chunk. It is
    what the grounding check verifies against, and it is why a generated
    citation cannot be invented: an item whose quote is not found in its cited
    chunk is flagged rather than published.
    """

    stem: str
    options: list[str]
    correct_index: int
    explanation: str
    source_quote: str
    #: Free-form generator diagnostics (strategy used, etc.), for auditing.
    metadata: dict = field(default_factory=dict)

    @property
    def correct_option(self) -> str:
        return self.options[self.correct_index]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Turns text into fixed-dimension vectors for similarity search."""

    name: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Must be deterministic for a given input."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Drafts question candidates from source text."""

    name: str

    def draft_questions(
        self,
        *,
        chunk_text: str,
        distractor_pool: list[str],
        max_questions: int = 1,
    ) -> list[QuestionDraft]:
        """Propose questions answerable from `chunk_text` alone.

        `distractor_pool` supplies text from elsewhere in the same document, so
        wrong options are real statements rather than invented ones.
        """
        ...
