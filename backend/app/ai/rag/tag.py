"""Competency tagging by embedding similarity.

This is an AI *suggestion*, and it is treated as one. A tag below the
confidence threshold is left empty rather than guessed, and every tag is
presented to a subject matter expert for confirmation. Nothing here influences
a competency score - tagging only decides which competency a question is filed
under.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.providers.base import EmbeddingProvider

# A tag is accepted only when the best match is both close enough in absolute
# terms AND clearly closer than the runner-up.
#
# The margin rule carries most of the weight. Absolute cosine between a short
# competency description and a longer passage is scale-dependent - measured
# across the sample corpus, correct matches landed anywhere between 0.09 and
# 0.32 - so a fixed absolute cut-off either rejects good tags or admits noise.
# "Clearly closest" is the robust signal, and it survives swapping in a
# different embedding model, where absolute values would shift again.
TAG_MIN_SCORE = 0.10
TAG_MIN_MARGIN = 1.25


@dataclass(frozen=True)
class TagSuggestion:
    competency_id: int | None
    score: float | None
    note: str | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    # Provider vectors are already L2-normalised, so the dot product is cosine.
    return max(-1.0, min(1.0, dot))


def suggest_competency(
    *,
    text: str,
    competencies: list[tuple[int, str]],
    embedder: EmbeddingProvider,
) -> TagSuggestion:
    """Suggest the closest competency for a passage.

    `competencies` is a list of (id, descriptive text) pairs - typically the
    competency name joined with its description.
    """
    if not competencies:
        return TagSuggestion(None, None, "No competencies are defined to tag against.")

    vectors = embedder.embed([text] + [description for _, description in competencies])
    query, candidates = vectors[0], vectors[1:]

    scored = [
        (competency_id, _cosine(query, candidate))
        for (competency_id, _), candidate in zip(competencies, candidates, strict=True)
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    best_id, best_score = scored[0]
    runner_up = scored[1][1] if len(scored) > 1 else 0.0

    if best_score < TAG_MIN_SCORE:
        return TagSuggestion(
            None,
            round(best_score, 4),
            (
                f"No competency matched closely enough (best {best_score:.2f}, "
                f"minimum {TAG_MIN_SCORE:.2f}). Left untagged for expert review."
            ),
        )

    margin = best_score / runner_up if runner_up > 0 else float("inf")
    if margin < TAG_MIN_MARGIN:
        return TagSuggestion(
            None,
            round(best_score, 4),
            (
                f"Two competencies matched almost equally well ({best_score:.2f} "
                f"vs {runner_up:.2f}). Left untagged rather than guessed - an "
                "expert should decide."
            ),
        )

    return TagSuggestion(best_id, round(best_score, 4))


def tagging_text(section_title: str | None, content: str, lead_chars: int = 300) -> str:
    """Build the passage representation used for tagging.

    A heading plus the opening of a passage identifies its topic better than
    the full text does: trailing detail dilutes the signal in a bag-of-words
    representation without adding topical information.
    """
    lead = content[:lead_chars]
    return f"{section_title}. {lead}" if section_title else lead
