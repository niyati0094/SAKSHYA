"""Vector storage adapters.

`get_vector_store` picks the implementation from the configured database URL,
so switching to PostgreSQL changes the retrieval backend without touching the
RAG pipeline.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.vectorstore.base import SearchHit, VectorStore
from app.vectorstore.numpy_store import NumpyVectorStore


def get_vector_store(db: Session) -> VectorStore:
    if get_settings().database_url.startswith("postgresql"):
        # Unverified in this environment - see pgvector_store module docstring.
        from app.vectorstore.pgvector_store import PgVectorStore

        return PgVectorStore(db)
    return NumpyVectorStore(db)


__all__ = ["NumpyVectorStore", "SearchHit", "VectorStore", "get_vector_store"]
