"""Document ingestion: store, extract, chunk, embed."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import get_embedding_provider
from app.ai.rag.chunk import chunk_pages
from app.ai.rag.extract import ExtractionError, extract
from app.core.config import get_settings
from app.models.document import Document, DocumentChunk, DocumentStatus

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def storage_dir() -> Path:
    directory = Path(get_settings().upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_upload(filename: str, data: bytes) -> Path:
    """Write bytes to disk under a generated name.

    The client-supplied filename is never used as a path: it is sanitised and
    prefixed with a UUID, so a crafted name cannot escape the upload directory
    or overwrite an existing file.
    """
    safe = _SAFE_NAME_RE.sub("_", Path(filename).name)[:120] or "upload"
    path = storage_dir() / f"{uuid.uuid4().hex}_{safe}"
    path.write_bytes(data)
    return path


def ingest_document(
    db: Session,
    *,
    title: str,
    filename: str,
    content_type: str | None,
    data: bytes,
    uploaded_by_id: int | None,
    is_prototype_data: bool = True,
) -> Document:
    """Full ingestion pipeline. Raises ExtractionError if the file is unusable.

    Extraction failure is recorded on the document row rather than losing the
    upload, so the UI can explain what went wrong.
    """
    path = save_upload(filename, data)

    document = Document(
        title=title.strip() or filename,
        filename=filename,
        content_type=content_type or "application/octet-stream",
        stored_path=str(path),
        byte_size=len(data),
        status=DocumentStatus.PROCESSING,
        uploaded_by_id=uploaded_by_id,
        is_prototype_data=is_prototype_data,
    )
    db.add(document)
    db.flush()

    try:
        pages = extract(str(path), filename, content_type)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ExtractionError("The document produced no usable passages.")
    except ExtractionError as exc:
        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)
        db.commit()
        raise

    embedder = get_embedding_provider()
    vectors = embedder.embed([chunk.content for chunk in chunks])

    for chunk, vector in zip(chunks, vectors):
        db.add(
            DocumentChunk(
                document_id=document.id,
                sequence=chunk.sequence,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                content=chunk.content,
                char_count=len(chunk.content),
                embedding=json.dumps([round(value, 6) for value in vector]),
                embedding_model=embedder.name,
            )
        )

    document.page_count = len({page.page_number for page in pages if page.page_number})
    document.chunk_count = len(chunks)
    document.status = DocumentStatus.READY
    document.error_message = None

    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.uploaded_at.desc())))


def get_document(db: Session, document_id: int) -> Document | None:
    return db.get(Document, document_id)


def get_chunks(db: Session, document_id: int) -> list[DocumentChunk]:
    return list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.sequence)
        )
    )


def search_chunks(db: Session, query: str, *, document_id: int | None = None, limit: int = 5):
    """Retrieve the passages most relevant to a query."""
    from app.vectorstore import get_vector_store

    embedder = get_embedding_provider()
    query_vector = embedder.embed([query])[0]
    hits = get_vector_store(db).search(query_vector, document_id=document_id, limit=limit)

    if not hits:
        return []

    by_id = {
        chunk.id: chunk
        for chunk in db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.id.in_([hit.chunk_id for hit in hits])
            )
        )
    }
    return [(by_id[hit.chunk_id], hit.score) for hit in hits if hit.chunk_id in by_id]
