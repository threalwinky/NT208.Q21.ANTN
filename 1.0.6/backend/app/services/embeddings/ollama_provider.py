from __future__ import annotations

from typing import Any

from app.services.embeddings.base import EmbeddingProvider
from app.services.ollama_service import OllamaService


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.ollama = OllamaService()

    async def embed(self, content: str | list[str]) -> list[float] | list[list[float]]:
        return await self.ollama.create_embedding(content)

    async def health(self) -> dict[str, Any]:
        return await self.ollama.health()
