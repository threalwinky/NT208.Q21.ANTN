from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        raise NotImplementedError
