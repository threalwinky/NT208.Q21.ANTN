from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.ollama_provider import OllamaEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider.lower().strip()
    if provider == "ollama":
        return OllamaEmbeddingProvider()
    raise RuntimeError("EMBEDDING_PROVIDER hiện chỉ hỗ trợ ollama.")
