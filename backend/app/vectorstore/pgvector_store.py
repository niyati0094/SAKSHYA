"""PostgreSQL + pgvector implementation of the VectorStore protocol.

    ⚠ NOT EXECUTED IN THIS ENVIRONMENT.

The development machine used to build this prototype has no Docker and no
pgvector extension available (see docs/ARCHITECTURE.md). This module is
written against the pgvector SQL interface and satisfies the same protocol as
`NumpyVectorStore`, but it has never been run, and must not be reported as
verified until it has been.

To use it:

1. Bring up PostgreSQL 16 with pgvector (see docker-compose.yml).
2. `CREATE EXTENSION IF NOT EXISTS vector;`
3. Store embeddings in a `vector(N)` column rather than the JSON text column
   the SQLite build uses, and add an index:
       CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
4. Point `SAKSHYA_DATABASE_URL` at PostgreSQL and construct this store instead
   of `NumpyVectorStore`.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.vectorstore.base import SearchHit


class PgVectorStore:
    """Cosine search delegated to pgvector's `<=>` distance operator."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def search(
        self,
        query_vector: list[float],
        *,
        document_id: int | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        # pgvector literal form: '[0.1,0.2,...]'
        literal = "[" + ",".join(f"{value:.6f}" for value in query_vector) + "]"

        filter_clause = "AND document_id = :document_id" if document_id is not None else ""
        statement = text(
            f"""
            SELECT id, 1 - (embedding <=> CAST(:query AS vector)) AS score
            FROM document_chunks
            WHERE embedding IS NOT NULL
            {filter_clause}
            ORDER BY embedding <=> CAST(:query AS vector)
            LIMIT :limit
            """
        )

        params: dict[str, object] = {"query": literal, "limit": limit}
        if document_id is not None:
            params["document_id"] = document_id

        rows = self._db.execute(statement, params).all()
        return [SearchHit(chunk_id=row.id, score=float(row.score)) for row in rows]
