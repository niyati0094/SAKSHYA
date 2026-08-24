"""Chunking that respects document structure.

Splitting on a fixed character count would cut sentences in half and produce
citations that quote fragments. This splits on headings and paragraph
boundaries first, packing whole paragraphs up to a target size, and only falls
back to sentence-level packing for paragraphs that are individually too long.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.rag.extract import ExtractedPage

TARGET_CHARS = 1100
MAX_CHARS = 1600
MIN_CHARS = 180

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
_NUMBERED_HEADING_RE = re.compile(r"^\s{0,3}(\d+(?:\.\d+)*)[.)]?\s+(?P<title>[A-Z][^\n]{3,80})$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


@dataclass(frozen=True)
class Chunk:
    sequence: int
    content: str
    page_number: int | None
    section_title: str | None


#: Below this many alphanumeric characters a passage cannot support a question
#: and only adds noise to retrieval (rule lines, stray headings).
MIN_MEANINGFUL_CHARS = 60


def chunk_pages(pages: list[ExtractedPage]) -> list[Chunk]:
    chunks: list[Chunk] = []
    sequence = 0
    current_section: str | None = None

    for page in pages:
        for block, section in _blocks_with_sections(page.text, current_section):
            current_section = section
            for content in _pack(block):
                if not _is_meaningful(content):
                    continue
                chunks.append(
                    Chunk(
                        sequence=sequence,
                        content=content,
                        page_number=page.page_number,
                        section_title=section,
                    )
                )
                sequence += 1

    return chunks


def _blocks_with_sections(text: str, inherited: str | None):
    """Yield (paragraph-group, section title), tracking the current heading."""
    section = inherited
    buffer: list[str] = []

    for raw in text.split("\n"):
        line = raw.strip()

        heading = _heading_of(line)
        if heading is not None:
            if buffer:
                yield "\n".join(buffer), section
                buffer = []
            section = heading
            continue

        if line:
            buffer.append(line)
        elif buffer:
            yield "\n".join(buffer), section
            buffer = []

    if buffer:
        yield "\n".join(buffer), section


def _is_meaningful(content: str) -> bool:
    return sum(character.isalnum() for character in content) >= MIN_MEANINGFUL_CHARS


def _heading_of(line: str) -> str | None:
    markdown = _HEADING_RE.match(line)
    if markdown:
        return markdown.group("title").strip()
    numbered = _NUMBERED_HEADING_RE.match(line)
    if numbered:
        return numbered.group("title").strip()
    return None


def _pack(block: str) -> list[str]:
    """Pack paragraphs to the target size, splitting only when unavoidable."""
    paragraphs = [p.strip() for p in block.split("\n") if p.strip()]
    packed: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > MAX_CHARS:
            if current:
                packed.append(current)
                current = ""
            packed.extend(_split_sentences(paragraph))
            continue

        candidate = f"{current} {paragraph}".strip() if current else paragraph
        if len(candidate) <= TARGET_CHARS:
            current = candidate
        else:
            if current:
                packed.append(current)
            current = paragraph

    if current:
        packed.append(current)

    # Fold a trailing scrap into its predecessor rather than emitting a chunk
    # too small to answer a question from.
    if len(packed) > 1 and len(packed[-1]) < MIN_CHARS:
        tail = packed.pop()
        packed[-1] = f"{packed[-1]} {tail}"

    return packed


def _split_sentences(paragraph: str) -> list[str]:
    sentences = _SENTENCE_RE.split(paragraph)
    out: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= TARGET_CHARS:
            current = candidate
        else:
            if current:
                out.append(current)
            current = sentence

    if current:
        out.append(current)
    return out
