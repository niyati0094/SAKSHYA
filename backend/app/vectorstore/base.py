"""Vector store interface.

Retrieval sits behind this protocol so the storage engine is a deployment
decision rather than an architectural one. Two implementations exist:

* `NumpyVectorStore` - exact cosine similarity, used locally. Verified.
* `PgVectorStore`    - PostgreSQL + pgvector. NOT executed in this
                       environment; see docs/ARCHITECTURE.md.

Exact search returns the same neighbours an approximate index would over a
corpus this size; the index matters at a scale this prototype does not reach.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    score: float


@runtime_checkable
class VectorStore(Protocol):
    def search(
        self,
        query_vector: list[float],
        *,
        document_id: int | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        """Return the closest chunks by cosine similarity, best first."""
        ...
