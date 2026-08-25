"""Document upload, inspection and retrieval endpoints."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.rag.extract import ExtractionError
from app.core.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.document import ChunkOut, DocumentOut, SearchHitOut
from app.services import document_service as service

router = APIRouter(prefix="/documents", tags=["documents"])

require_content_manager = require_roles(UserRole.SME, UserRole.ADMIN)

#: Upload read size. Bounds peak memory to roughly the configured limit.
_READ_CHUNK_BYTES = 64 * 1024


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    current_user: User = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Upload learning material and run the ingestion pipeline.

    Ingestion is synchronous: the response is only returned once the document
    has actually been extracted, chunked and embedded, so a 201 means the
    document is genuinely searchable rather than merely accepted.
    """
    settings = get_settings()

    # Read in chunks and stop at the limit. Reading the whole upload first and
    # checking its size afterwards would let an oversized file exhaust memory
    # before the check ever ran - the limit has to be enforced while reading.
    buffer = bytearray()
    while chunk := await file.read(_READ_CHUNK_BYTES):
        buffer.extend(chunk)
        if len(buffer) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit."
                ),
            )

    data = bytes(buffer)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty."
        )

    try:
        document = service.ingest_document(
            db,
            title=title or file.filename or "Untitled",
            filename=file.filename or "upload",
            content_type=file.content_type,
            data=data,
            uploaded_by_id=current_user.id,
        )
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return DocumentOut.model_validate(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentOut]:
    return [DocumentOut.model_validate(item) for item in service.list_documents(db)]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    document = service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentOut.model_validate(document)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def get_chunks(
    document_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChunkOut]:
    if service.get_document(db, document_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return [ChunkOut.model_validate(chunk) for chunk in service.get_chunks(db, document_id)]


@router.get("/{document_id}/search", response_model=list[SearchHitOut])
def search_document(
    document_id: int,
    q: str = Query(min_length=2, max_length=500),
    limit: int = Query(default=5, ge=1, le=20),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SearchHitOut]:
    """Semantic retrieval over one document's chunks."""
    if service.get_document(db, document_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    results = service.search_chunks(db, q, document_id=document_id, limit=limit)
    return [
        SearchHitOut(chunk=ChunkOut.model_validate(chunk), score=round(score, 4))
        for chunk, score in results
    ]
