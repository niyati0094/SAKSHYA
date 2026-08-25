"""Learning catalogue adapters.

`get_catalog()` resolves the active adapter. Only the local prototype
catalogue is implemented in this build; an iGOT Karmayogi adapter is added by
implementing `LearningCatalogAdapter` and registering it here, with no change
to the recommender.
"""

from __future__ import annotations

from functools import lru_cache

from app.catalog.base import LearningCatalogAdapter, LearningResource, ResourceKind
from app.catalog.local_adapter import LocalCatalogAdapter

#: Adapters available in this build. "igot" is deliberately absent: no live
#: integration exists, and offering the name would imply one does.
AVAILABLE_ADAPTERS = ("local",)


@lru_cache
def get_catalog() -> LearningCatalogAdapter:
    return LocalCatalogAdapter()


__all__ = [
    "AVAILABLE_ADAPTERS",
    "LearningCatalogAdapter",
    "LearningResource",
    "LocalCatalogAdapter",
    "ResourceKind",
    "get_catalog",
]
