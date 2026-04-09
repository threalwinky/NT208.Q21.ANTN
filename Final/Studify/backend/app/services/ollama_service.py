from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings


class OllamaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_embedding(self, content: str | list[str]) -> list[float] | list[list[float]]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/embed",
                json={"model": self.settings.ollama_embed_model, "input": content},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings")
            if isinstance(content, list):
                return embeddings or []
            if embeddings:
                return embeddings[0]
            return data.get("embedding", [])

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
