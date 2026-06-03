"""
LLM provider dùng OpenAI Chat Completions API + function-calling (tools).

Endpoint + API key được cấu hình qua .env (GPT_BASE_URL, GPT_API_KEY,
GPT_CHAT_MODEL) — không hardcode trong mã nguồn.
- Non-stream: POST {GPT_BASE_URL}/chat/completions -> choices[0].message.content
- Stream:     POST .../chat/completions (stream=true) -> SSE chuẩn OpenAI
              data: {"choices":[{"delta":{"content":"..."}}]} ... data: [DONE]

Hỗ trợ tool-calling (web_search) theo chuẩn OpenAI:
- Gửi `tools=[web_search]`; nếu model trả `tool_calls` (non-stream) hoặc
  `delta.tool_calls` (stream) thì thực thi web_search, gửi lại `role:"tool"`
  rồi lặp cho tới khi model trả lời.

Lưu ý router (đã kiểm chứng): KHÔNG gửi `tool_choice` và dùng `content:""`
cho assistant tool_calls message (gửi `content:null` + `tool_choice` gây 502).
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mimo_provider import TOOL_STATUS_PREFIX

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 3
# Router đôi khi trả 502/503/504 tạm thời (proxy tới reasoning model) → retry có backoff.
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = (0.8, 1.6, 2.4)
_RETRY_STATUS = {502, 503, 504, 429}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRY_STATUS
    return isinstance(exc, (httpx.TransportError, httpx.ReadError, httpx.ConnectError))


def _coerce_content(content: Any) -> str:
    """Chuẩn hoá content về string (phòng trường hợp content là list block)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [str(block.get("text", "")) for block in content if isinstance(block, dict)]
        return "".join(parts)
    return "" if content is None else str(content)


def _prepare_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gộp mọi system message thành một (đặt đầu), giữ nguyên thứ tự user/assistant.

    Chỉ áp dụng cho input ban đầu từ chat_service (chỉ có role system/user/assistant
    dạng string). Các message tool (assistant.tool_calls / role tool) sinh trong
    vòng lặp được append trực tiếp ở dạng OpenAI, KHÔNG đi qua hàm này.
    """
    system_parts: list[str] = []
    conversation: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = _coerce_content(msg.get("content", ""))
        if role == "system":
            if content:
                system_parts.append(content)
        else:
            conversation.append({"role": "assistant" if role == "assistant" else "user", "content": content})

    result: list[dict[str, Any]] = []
    if system_parts:
        result.append({"role": "system", "content": "\n\n".join(system_parts)})
    result.extend(conversation)
    if not any(m["role"] == "user" for m in result):
        result.append({"role": "user", "content": "Xin chào"})
    return result


class OpenAICompatProvider(LLMProvider):
    """LLM provider dùng OpenAI Chat Completions-compatible endpoint (GPT-5.5)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def _endpoint(self) -> str:
        base_url = self.settings.gpt_base_url.strip()
        if not base_url:
            raise RuntimeError("GPT_BASE_URL chưa được cấu hình (đặt trong .env).")
        return f"{base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        api_key = self.settings.gpt_api_key.strip()
        if not api_key:
            raise RuntimeError("GPT_API_KEY chưa được cấu hình.")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ─── tools ────────────────────────────────────────────────────────────────

    def _tools(self, web_search_enabled: bool) -> list[dict[str, Any]] | None:
        if not web_search_enabled or not self.settings.enable_web_search:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": (
                        "Tìm kiếm thông tin trên internet. Dùng khi knowledge base không đủ "
                        "thông tin, hoặc câu hỏi về sự kiện/thông báo mới nhất ngoài tầm dữ liệu."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Từ khoá tìm kiếm. Ưu tiên tiếng Việt cho thông tin UIT.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

    async def _execute_tool(self, name: str, args: dict[str, Any], max_results: int | None) -> str:
        if name == "web_search":
            query = str(args.get("query", "")).strip()
            if not query:
                return "Thiếu từ khoá tìm kiếm."
            limit = max_results or self.settings.web_search_max_results
            logger.info("[gpt] web_search query: %s", query)
            try:
                from app.services.web_search_service import WebSearchService

                return await WebSearchService().search(query, max_results=limit)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[gpt] web_search thất bại: %s", exc)
                return f"Không tìm kiếm được: {exc}"
        logger.warning("[gpt] tool không hỗ trợ: %s", name)
        return "Tool này không được hỗ trợ. Hãy trả lời dựa trên thông tin đã có, không gọi thêm tool."

    # ─── payload + request ──────────────────────────────────────────────────────

    def _payload(self, messages: list[dict[str, Any]], stream: bool, tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.gpt_chat_model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            # KHÔNG gửi tool_choice (mặc định "auto") để tránh lỗi 502 của router.
        if self.settings.gpt_temperature is not None:
            payload["temperature"] = self.settings.gpt_temperature
        if self.settings.gpt_max_tokens:
            payload["max_tokens"] = self.settings.gpt_max_tokens
        return payload

    async def _post_json(self, client: httpx.AsyncClient, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.post(self._endpoint, headers=self._headers(), json=self._payload(messages, False, tools))
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                    raise
                last_exc = exc
                wait = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning("[gpt] %s → retry %d sau %.1fs", exc, attempt + 1, wait)
                await asyncio.sleep(wait)
        raise last_exc or RuntimeError("gpt request thất bại")

    @staticmethod
    def _query_of(tool_call: dict[str, Any]) -> str:
        fn = tool_call.get("function") or {}
        try:
            return str(json.loads(fn.get("arguments") or "{}").get("query", "")).strip()
        except (json.JSONDecodeError, AttributeError):
            return ""

    # ─── non-streaming chat (agentic loop) ────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> str:
        timeout = httpx.Timeout(float(self.settings.gpt_timeout_seconds), connect=20.0)
        working: list[dict[str, Any]] = _prepare_messages(messages)
        tools = self._tools(web_search_enabled)

        async with httpx.AsyncClient(timeout=timeout) as client:
            for iteration in range(_MAX_TOOL_ITERATIONS):
                # Vòng cuối: bỏ tools để buộc model trả lời.
                use_tools = tools if iteration < _MAX_TOOL_ITERATIONS - 1 else None
                data = await self._post_json(client, working, use_tools)
                message = (data.get("choices") or [{}])[0].get("message") or {}
                tool_calls = message.get("tool_calls") or []

                if not tool_calls:
                    return _coerce_content(message.get("content", "")).strip()

                logger.info("[gpt] chat tool use #%d: %s", iteration, [tc.get("function", {}).get("name") for tc in tool_calls])
                working.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    result = await self._execute_tool(fn.get("name", ""), self._safe_args(fn), web_search_max_results)
                    working.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result})

        return ""

    @staticmethod
    def _safe_args(fn: dict[str, Any]) -> dict[str, Any]:
        try:
            parsed = json.loads(fn.get("arguments") or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    # ─── streaming chat (agentic loop) ────────────────────────────────────────

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> AsyncIterator[str]:  # type: ignore[override]
        timeout = httpx.Timeout(None, connect=20.0)
        working: list[dict[str, Any]] = _prepare_messages(messages)
        tools = self._tools(web_search_enabled)
        produced = False

        async with httpx.AsyncClient(timeout=timeout) as client:
            for iteration in range(_MAX_TOOL_ITERATIONS):
                use_tools = tools if iteration < _MAX_TOOL_ITERATIONS - 1 else None
                content_acc = ""
                tool_acc: dict[int, dict[str, str]] = {}
                turn_ok = False

                for attempt in range(_MAX_RETRIES):
                    content_acc = ""
                    tool_acc = {}
                    attempt_produced = False
                    try:
                        async with client.stream(
                            "POST", self._endpoint, headers=self._headers(), json=self._payload(working, True, use_tools)
                        ) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data:"):
                                    continue
                                raw = line[5:].strip()
                                if raw == "[DONE]":
                                    break
                                try:
                                    evt = json.loads(raw)
                                except json.JSONDecodeError:
                                    continue
                                choices = evt.get("choices") or []
                                if not choices:
                                    continue
                                delta = choices[0].get("delta") or {}
                                piece = delta.get("content")
                                if piece:
                                    produced = True
                                    attempt_produced = True
                                    content_acc += piece
                                    yield piece
                                for tc in delta.get("tool_calls") or []:
                                    idx = tc.get("index", 0)
                                    slot = tool_acc.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                                    if tc.get("id"):
                                        slot["id"] = tc["id"]
                                    fn = tc.get("function") or {}
                                    if fn.get("name"):
                                        slot["name"] = fn["name"]
                                    if fn.get("arguments"):
                                        slot["arguments"] += fn["arguments"]
                        turn_ok = True
                        break
                    except httpx.HTTPError as exc:
                        # Chỉ retry khi attempt này CHƯA yield chữ nào (tránh lặp output).
                        if attempt_produced or not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                            logger.error("[gpt] stream lỗi: %s", exc)
                            if not produced:
                                try:
                                    data = await self._post_json(client, working, None)
                                    text = _coerce_content(((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")).strip()
                                    if text:
                                        yield text
                                except httpx.HTTPError:
                                    pass
                            return
                        wait = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                        logger.warning("[gpt] stream %s → retry %d sau %.1fs", exc, attempt + 1, wait)
                        await asyncio.sleep(wait)

                if not turn_ok:
                    return

                if not tool_acc:
                    return  # model đã trả lời (content đã stream) hoặc rỗng → kết thúc

                # Có tool calls → thực thi rồi lặp tiếp để stream câu trả lời cuối.
                tool_calls = [
                    {
                        "id": slot["id"],
                        "type": "function",
                        "function": {"name": slot["name"], "arguments": slot["arguments"]},
                    }
                    for _, slot in sorted(tool_acc.items())
                ]
                working.append({"role": "assistant", "content": content_acc, "tool_calls": tool_calls})
                for tc in tool_calls:
                    name = tc["function"]["name"]
                    if name == "web_search":
                        query = self._query_of(tc)
                        if query:
                            yield f"{TOOL_STATUS_PREFIX}Đang tìm trên web: {query[:60]}"
                    result = await self._execute_tool(name, self._safe_args(tc["function"]), web_search_max_results)
                    working.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

        if not produced:
            # Hết số vòng mà chưa có chữ nào → gọi non-stream lần cuối cho chắc.
            text = await self.chat(messages, web_search_enabled=False, web_search_max_results=web_search_max_results)
            if text:
                yield text

    # ─── health ─────────────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        model = self.settings.gpt_chat_model
        if not self.settings.gpt_api_key.strip() or not self.settings.gpt_base_url.strip():
            return {"provider": "gpt", "format": "openai", "configured": False, "model": model}
        timeout = httpx.Timeout(20.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    self._endpoint,
                    headers=self._headers(),
                    json={"model": model, "stream": False, "messages": [{"role": "user", "content": "ping"}]},
                )
                resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return {"provider": "gpt", "format": "openai", "configured": True, "model": model, "status": "error", "error": str(exc)}
        return {"provider": "gpt", "format": "openai", "configured": True, "model": model, "status": "ok"}
