from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.services.llm.base import LLMProvider
from app.services.ollama_service import OllamaService


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self.ollama = OllamaService()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> str:
        return await self.ollama.chat(messages)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> AsyncIterator[str]:
        async for delta in self.ollama.stream_chat(messages):
            yield delta

    async def health(self) -> dict[str, Any]:
        return await self.ollama.health()
