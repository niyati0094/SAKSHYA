"""Text extraction from uploaded material, preserving page provenance.

Page numbers are carried through extraction because a citation without a
locator is not verifiable. Where a format has no pages (Markdown, plain text)
the page is recorded as None and the section heading is used instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedPage:
    """One page (or one section, for page-less formats) of source text."""

    page_number: int | None
    text: str


class ExtractionError(RuntimeError):
    """Raised when a file cannot be read as text."""


SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "text/markdown": "text",
    "text/plain": "text",
    "text/x-markdown": "text",
}

SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".md": "text", ".txt": "text"}


def detect_kind(filename: str, content_type: str | None) -> str:
    """Resolve a handler from the content type, falling back to the extension."""
    if content_type and content_type.lower() in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[content_type.lower()]

    lowered = filename.lower()
    for extension, kind in SUPPORTED_EXTENSIONS.items():
        if lowered.endswith(extension):
            return kind

    raise ExtractionError(
        f"Unsupported file type '{content_type or filename}'. "
        "Upload a PDF, Markdown or plain text file."
    )


def extract_pdf(path: str) -> list[ExtractedPage]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
    except Exception as exc:  # pragma: no cover - malformed file path
        raise ExtractionError(f"Could not open the PDF: {exc}") from exc

    pages: list[ExtractedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        cleaned = _clean(text)
        if cleaned:
            pages.append(ExtractedPage(page_number=index, text=cleaned))

    if not pages:
        raise ExtractionError(
            "No text could be extracted. The PDF may be a scanned image, which "
            "would require OCR."
        )
    return pages


def extract_text_file(path: str) -> list[ExtractedPage]:
    with open(path, encoding="utf-8", errors="replace") as handle:
        content = handle.read()

    cleaned = _clean(content)
    if not cleaned:
        raise ExtractionError("The file contains no readable text.")
    return [ExtractedPage(page_number=None, text=cleaned)]


def extract(path: str, filename: str, content_type: str | None) -> list[ExtractedPage]:
    kind = detect_kind(filename, content_type)
    return extract_pdf(path) if kind == "pdf" else extract_text_file(path)


def _clean(text: str) -> str:
    """Normalise whitespace without destroying paragraph boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Join words split across line breaks by PDF layout.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Collapse single newlines inside a paragraph, keep blank-line breaks.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
