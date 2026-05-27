from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


class MimoProvider(LLMProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def endpoint(self) -> str:
        return f"{self.settings.mimo_base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        api_key = self.settings.mimo_api_key.strip()
        if not api_key:
            raise RuntimeError("MIMO_API_KEY chưa được cấu hình.")
        return {"api-key": api_key, "Content-Type": "application/json"}

    def _payload(self, messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
        return {
            "model": self.settings.mimo_chat_model,
            "messages": messages,
            "max_completion_tokens": self.settings.mimo_max_completion_tokens,
            "temperature": self.settings.mimo_temperature,
            "top_p": self.settings.mimo_top_p,
            "stream": stream,
            "stop": None,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }

    async def chat(self, messages: list[dict[str, str]]) -> str:
        timeout = httpx.Timeout(float(self.settings.mimo_timeout_seconds), connect=20.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.endpoint, headers=self._headers(), json=self._payload(messages, stream=False))
            response.raise_for_status()
            data = response.json()
        return str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if not self.settings.enable_mimo_streaming:
            content = await self.chat(messages)
            if content:
                yield content
            return

        timeout = httpx.Timeout(None, connect=20.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", self.endpoint, headers=self._headers(), json=self._payload(messages, stream=True)) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    text = line.strip()
                    if not text:
                        continue
                    if text.startswith("data:"):
                        text = text[5:].strip()
                    if text == "[DONE]":
                        break
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    delta = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta is None:
                        delta = payload.get("choices", [{}])[0].get("message", {}).get("content")
                    if delta:
                        yield str(delta)

    async def health(self) -> dict[str, Any]:
        if not self.settings.mimo_api_key.strip():
            return {"provider": "mimo", "configured": False, "model": self.settings.mimo_chat_model}
        timeout = httpx.Timeout(20.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.endpoint,
                headers=self._headers(),
                json={
                    "model": self.settings.mimo_chat_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_completion_tokens": 8,
                    "temperature": 0,
                    "top_p": 1,
                    "stream": False,
                },
            )
            response.raise_for_status()
        return {"provider": "mimo", "configured": True, "model": self.settings.mimo_chat_model, "status": "ok"}
