"""Exact cosine similarity search over stored chunk embeddings.

Vectors are persisted as JSON on the chunk row and loaded into a numpy matrix
per query. For a demo corpus (hundreds of chunks) this is instant and exact.
"""

from __future__ import annotations

import json

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.vectorstore.base import SearchHit


class NumpyVectorStore:
    """Cosine similarity search backed by the relational chunk table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def search(
        self,
        query_vector: list[float],
        *,
        document_id: int | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        statement = select(DocumentChunk).where(DocumentChunk.embedding.is_not(None))
        if document_id is not None:
            statement = statement.where(DocumentChunk.document_id == document_id)

        chunks = list(self._db.scalars(statement))
        if not chunks:
            return []

        query = np.asarray(query_vector, dtype=np.float32)
        query_norm = float(np.linalg.norm(query))
        if query_norm == 0.0:
            return []

        matrix = np.asarray(
            [json.loads(chunk.embedding) for chunk in chunks], dtype=np.float32
        )
        norms = np.linalg.norm(matrix, axis=1)
        # Guard against zero-length vectors (a chunk of pure stopwords).
        norms[norms == 0.0] = 1.0

        scores = (matrix @ query) / (norms * query_norm)

        order = np.argsort(-scores)[:limit]
        return [
            SearchHit(chunk_id=chunks[int(index)].id, score=float(scores[int(index)]))
            for index in order
            if float(scores[int(index)]) > 0.0
        ]
