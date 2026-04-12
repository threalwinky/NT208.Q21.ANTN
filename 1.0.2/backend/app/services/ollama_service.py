from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings


class OllamaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        content: str | list[str],
    ) -> list[list[float]]:
        response = await client.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/embed",
            json={"model": self.settings.ollama_embed_model, "input": content},
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if embeddings:
            return embeddings
        embedding = data.get("embedding")
        if isinstance(embedding, list) and embedding and isinstance(embedding[0], (int, float)):
            return [embedding]
        return []

    async def create_embedding(self, content: str | list[str]) -> list[float] | list[list[float]]:
        is_single = isinstance(content, str)
        inputs = [content] if is_single else [item for item in content if item]
        if not inputs:
            return [] if is_single else []

        timeout = httpx.Timeout(180.0, connect=20.0)
        all_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=timeout) as client:
            for index in range(0, len(inputs), 8):
                batch = inputs[index : index + 8]
                try:
                    all_embeddings.extend(await self._embed_batch(client, batch))
                    continue
                except httpx.TimeoutException:
                    pass

                for item in batch:
                    item_embedding: list[list[float]] = []
                    last_error: Exception | None = None
                    for attempt in range(3):
                        try:
                            item_embedding = await self._embed_batch(client, item)
                            break
                        except httpx.TimeoutException as exc:
                            last_error = exc
                            await asyncio.sleep(0.75 * (attempt + 1))
                    if not item_embedding:
                        if last_error is not None:
                            raise last_error
                        raise RuntimeError("Không nhận được embedding từ Ollama.")
                    all_embeddings.extend(item_embedding)

        if is_single:
            return all_embeddings[0] if all_embeddings else []
        return all_embeddings

    async def chat(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": self.settings.ollama_chat_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.35, "num_ctx": 6144},
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data.get("message", {}).get("content", "").strip()

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": self.settings.ollama_chat_model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.35, "num_ctx": 6144},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    if payload.get("error"):
                        raise RuntimeError(str(payload["error"]))
                    delta = payload.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if payload.get("done"):
                        break

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            return response.json()
