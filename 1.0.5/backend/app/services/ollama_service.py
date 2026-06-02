from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings


class OllamaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _candidate_base_urls(self) -> list[str]:
        candidates: list[str] = []

        def add(url: str) -> None:
            normalized = (url or "").strip().rstrip("/")
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        add(self.settings.ollama_base_url)
        if self.settings.ollama_fallback_urls:
            for item in self.settings.ollama_fallback_urls.split(","):
                add(item)

        primary_host = urlparse(self.settings.ollama_base_url).hostname or ""
        if primary_host == "host.docker.internal":
            add("http://10.0.0.1:11434")
            add("http://172.17.0.1:11434")
            add("http://127.0.0.1:11434")
        elif primary_host in {"127.0.0.1", "localhost"}:
            add("http://host.docker.internal:11434")
            add("http://10.0.0.1:11434")

        return candidates

    def _format_connection_error(self, operation: str, errors: list[str]) -> RuntimeError:
        detail = " | ".join(errors) if errors else "không có chi tiết lỗi"
        return RuntimeError(f"Không kết nối được Ollama khi {operation}. Đã thử: {detail}")

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        content: str | list[str],
    ) -> list[list[float]]:
        response = await client.post(
            f"{base_url}/api/embed",
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
                batch_embedded = False
                batch_errors: list[str] = []
                for base_url in self._candidate_base_urls():
                    try:
                        all_embeddings.extend(await self._embed_batch(client, base_url, batch))
                        batch_embedded = True
                        break
                    except Exception as exc:
                        batch_errors.append(f"{base_url} -> {exc}")
                if batch_embedded:
                    continue

                for item in batch:
                    item_embedding: list[list[float]] = []
                    item_errors: list[str] = []
                    for attempt in range(3):
                        for base_url in self._candidate_base_urls():
                            try:
                                item_embedding = await self._embed_batch(client, base_url, item)
                                break
                            except Exception as exc:
                                item_errors.append(f"{base_url} -> {exc}")
                        if item_embedding:
                            break
                        await asyncio.sleep(0.75 * (attempt + 1))
                    if not item_embedding:
                        raise self._format_connection_error("tạo embedding", item_errors or batch_errors)
                    all_embeddings.extend(item_embedding)

        if is_single:
            return all_embeddings[0] if all_embeddings else []
        return all_embeddings

    async def chat(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            errors: list[str] = []
            for base_url in self._candidate_base_urls():
                try:
                    response = await client.post(
                        f"{base_url}/api/chat",
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
                except Exception as exc:
                    errors.append(f"{base_url} -> {exc}")
            raise self._format_connection_error("gọi chat model", errors)

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=None) as client:
            errors: list[str] = []
            for base_url in self._candidate_base_urls():
                yielded_any = False
                try:
                    async with client.stream(
                        "POST",
                        f"{base_url}/api/chat",
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
                                yielded_any = True
                                yield delta
                            if payload.get("done"):
                                break
                    return
                except Exception as exc:
                    if yielded_any:
                        raise self._format_connection_error("stream chat model", [f"{base_url} -> {exc}"])
                    errors.append(f"{base_url} -> {exc}")
            raise self._format_connection_error("stream chat model", errors)

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            errors: list[str] = []
            candidates = self._candidate_base_urls()
            for base_url in candidates:
                try:
                    response = await client.get(f"{base_url}/api/tags")
                    response.raise_for_status()
                    data = response.json()
                    data["active_base_url"] = base_url
                    data["candidate_base_urls"] = candidates
                    return data
                except Exception as exc:
                    errors.append(f"{base_url} -> {exc}")
            raise self._format_connection_error("kiểm tra health", errors)
