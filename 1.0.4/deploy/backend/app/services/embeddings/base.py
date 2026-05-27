from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, content: str | list[str]) -> list[float] | list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        raise NotImplementedError
