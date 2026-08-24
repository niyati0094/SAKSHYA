"""Provider selection.

Which implementation is used is a configuration decision, resolved here once.
Call sites ask for `get_embedding_provider()` and never name a vendor.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.providers.base import EmbeddingProvider, LLMProvider, QuestionDraft
from app.ai.providers.mock import MockEmbeddingProvider, MockLLMProvider
from app.core.config import get_settings

#: Implementations available in this build. A hosted provider is added by
#: registering it here; no call site changes.
AVAILABLE_PROVIDERS = ("mock",)


def _resolve(requested: str) -> str:
    name = (requested or "mock").strip().lower()
    if name not in AVAILABLE_PROVIDERS:
        raise RuntimeError(
            f"Unknown AI provider '{name}'. Available in this build: "
            f"{', '.join(AVAILABLE_PROVIDERS)}. "
            "Hosted providers are not implemented here - see docs/ARCHITECTURE.md."
        )
    return name


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    _resolve(get_settings().ai_provider)
    return MockEmbeddingProvider()


@lru_cache
def get_llm_provider() -> LLMProvider:
    _resolve(get_settings().ai_provider)
    return MockLLMProvider()


__all__ = [
    "AVAILABLE_PROVIDERS",
    "EmbeddingProvider",
    "LLMProvider",
    "QuestionDraft",
    "get_embedding_provider",
    "get_llm_provider",
]
