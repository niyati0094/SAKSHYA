"""Deterministic offline AI provider.

Used when no hosted model is configured, which is the default for this
prototype. Both implementations are fully deterministic and dependency-light:
identical input always yields identical output, no network call is made, and a
live demo cannot fail on an API outage.

Honest description of what this is and is not:

* The embedding provider is a hashed bag-of-words projection. It captures
  lexical overlap, which is sufficient to retrieve the right passage from a
  document-sized corpus. It does not capture paraphrase or synonymy the way a
  trained sentence encoder would.
* The question generator is *extractive*, not generative. Every stem, correct
  answer and distractor is lifted from real sentences in the source document.
  It cannot hallucinate a fact or invent a citation, because it never writes
  prose of its own - which is exactly the property the grounding requirement
  needs. It produces plainer questions than a hosted model would.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from app.ai.providers.base import QuestionDraft

# Wide enough that hashing collisions stay rare across a document-sized
# feature space. At 256 dimensions, unigram+bigram collisions were measurably
# degrading retrieval; the memory cost of 1024 is negligible at this scale.
EMBEDDING_DIMENSIONS = 1024

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """a an and are as at be been by for from has have in is it its of on or that the
    to was were which with within without this these those than then when where
    while such not but their there they can may must should would could each every
    all any into more most other some only same so if because""".split()
)


def _stable_hash(text: str) -> int:
    """Stable across processes, unlike Python's salted built-in hash()."""
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


def _tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS]


def _features(text: str) -> list[str]:
    """Unigrams plus adjacent bigrams, so short phrases carry some weight."""
    tokens = _tokenize(text)
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]


class MockEmbeddingProvider:
    """Hashed bag-of-words embeddings with sublinear term frequency."""

    name = "mock-hashed-bow"
    dimensions = EMBEDDING_DIMENSIONS

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        counts = Counter(_features(text))

        for feature, count in counts.items():
            index = _stable_hash(feature) % self.dimensions
            # Sublinear scaling: a term repeated ten times is not ten times as
            # important as one seen once.
            vector[index] += 1.0 + math.log(count)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


# ---------------------------------------------------------------------------
# Extractive question generation
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

# Numbers worth asking about, including spelled-out small integers.
_NUMBER_RE = re.compile(
    r"\b(\d{1,3}(?:\.\d+)?)\s?(percent|per cent)?\b|"
    r"\b(three|four|five|ten|twenty|thirty|sixty|seventy|ninety)\b",
    re.IGNORECASE,
)

_WORD_NUMBERS = {
    "three": 3,
    "four": 4,
    "five": 5,
    "ten": 10,
    "twenty": 20,
    "thirty": 30,
    "sixty": 60,
    "seventy": 70,
    "ninety": 90,
}

# Sentences that define or characterise a subject make the clearest questions.
# The subject is capped at five words: without that cap the pattern happily
# swallowed half a sentence ("A sampling frame is the list or procedure that")
# before reaching a verb, producing incoherent stems.
_DEFINITION_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z\-]*(?: [a-zA-Z\-]+){0,4}?)\s"
    r"(?P<verb>occurs when|is defined as|is normally|is rarely|refers to|"
    r"divides|replaces|detects|protects|groups|removes|identifies|reduces|"
    r"is|are)\s",
)

_LEADING_ARTICLE_RE = re.compile(r"^(a|an|the)\s+", re.IGNORECASE)

_MIN_SENTENCE_CHARS = 60
_MAX_SENTENCE_CHARS = 320


def split_sentences(text: str) -> list[str]:
    """Split into sentences, discarding fragments too short to stand alone."""
    normalised = re.sub(r"\s+", " ", text).strip()
    if not normalised:
        return []
    return [part.strip() for part in _SENTENCE_RE.split(normalised) if part.strip()]


def _usable(sentence: str) -> bool:
    return _MIN_SENTENCE_CHARS <= len(sentence) <= _MAX_SENTENCE_CHARS


def _perturb(value: float) -> list[float]:
    """Plausible wrong numbers: same order of magnitude, clearly different."""
    candidates = [value * 2, value / 2, value + max(1.0, round(value * 0.5))]
    seen: list[float] = []
    for candidate in candidates:
        rounded = round(candidate, 2)
        if rounded != round(value, 2) and rounded > 0 and rounded not in seen:
            seen.append(rounded)
    return seen


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _word_number_options(word: str) -> list[str]:
    """Distractors for a spelled-out number, kept in the same word form."""
    ladder = sorted(_WORD_NUMBERS, key=lambda key: _WORD_NUMBERS[key])
    position = ladder.index(word)
    neighbours = [
        ladder[index]
        for offset in (1, -1, 2, -2, 3)
        if 0 <= (index := position + offset) < len(ladder)
    ]
    seen: list[str] = []
    for candidate in neighbours:
        if candidate not in seen:
            seen.append(candidate)
    return [word] + seen[:3]


class MockLLMProvider:
    """Builds multiple-choice questions by extraction, never by invention."""

    name = "mock-extractive"

    def draft_questions(
        self,
        *,
        chunk_text: str,
        distractor_pool: list[str],
        max_questions: int = 1,
    ) -> list[QuestionDraft]:
        sentences = [s for s in split_sentences(chunk_text) if _usable(s)]
        drafts: list[QuestionDraft] = []

        for sentence in sentences:
            if len(drafts) >= max_questions:
                break

            draft = self._numeric_question(sentence) or self._definition_question(
                sentence, distractor_pool
            )
            if draft is not None:
                drafts.append(draft)

        return drafts

    # -- strategy 1: blank out a specific figure -----------------------------

    def _numeric_question(self, sentence: str) -> QuestionDraft | None:
        match = _NUMBER_RE.search(sentence)
        if match is None:
            return None

        literal = match.group(0).strip()
        digits, unit, word = match.group(1), match.group(2), match.group(3)

        if digits is not None:
            value = float(digits)
            suffix = f" {unit}" if unit else ""
            options = [f"{_format_number(value)}{suffix}"] + [
                f"{_format_number(alternative)}{suffix}" for alternative in _perturb(value)
            ]
        elif word is not None:
            # Keep spelled-out numbers in word form. Substituting the digit
            # would make the correct answer absent from the source text, and
            # grounding verification would (correctly) reject the question.
            options = _word_number_options(word.lower())
        else:
            return None

        if len(options) < 3:
            return None

        stem = (
            "Complete the statement from the source material: "
            + sentence.replace(literal, "______", 1)
        )
        correct = options[0]
        ordered = self._order_options(stem, options)

        return QuestionDraft(
            stem=stem,
            options=ordered,
            correct_index=ordered.index(correct),
            explanation=(
                "The source material states: "
                f"“{sentence}”"
            ),
            source_quote=sentence,
            metadata={"strategy": "numeric_cloze"},
        )

    # -- strategy 2: match a subject to its description ----------------------

    def _definition_question(
        self, sentence: str, distractor_pool: list[str]
    ) -> QuestionDraft | None:
        match = _DEFINITION_RE.match(sentence)
        if match is None:
            return None

        subject = _LEADING_ARTICLE_RE.sub("", match.group("subject").strip()).strip()
        if len(subject) < 4:
            return None

        # Distractors are real sentences from elsewhere in the same document,
        # about a different subject. They are true statements, but wrong
        # answers to this question - which makes them plausible without
        # requiring anything to be invented.
        candidates = [
            candidate
            for candidate in distractor_pool
            if _usable(candidate)
            and candidate != sentence
            and subject.lower() not in candidate.lower()
        ]
        # Deterministic pick, stable across runs for the same inputs.
        candidates.sort(key=lambda text: _stable_hash(subject + text))
        if len(candidates) < 3:
            return None

        options = [sentence] + candidates[:3]
        stem = f"Which statement about {subject.lower()} is supported by the source material?"
        ordered = self._order_options(stem, options)

        return QuestionDraft(
            stem=stem,
            options=ordered,
            correct_index=ordered.index(sentence),
            explanation=(
                f"The source material states this directly. The other options are "
                f"statements from the same document about different topics, so they do "
                f"not describe {subject.lower()}."
            ),
            source_quote=sentence,
            metadata={"strategy": "definition_match", "subject": subject},
        )

    @staticmethod
    def _order_options(stem: str, options: list[str]) -> list[str]:
        """Deterministic ordering, so the answer is not always first."""
        return sorted(options, key=lambda option: _stable_hash(stem + option))
