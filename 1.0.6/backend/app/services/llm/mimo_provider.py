"""
MiMo LLM provider – dùng Anthropic /v1/messages API.

Hỗ trợ:
- Chat không stream (agentic loop với tool use)
- Stream chat với Anthropic SSE events (text_delta realtime)
- Web search tool tích hợp (gọi khi không có đủ thông tin)
- Filtering thinking blocks trong output (chỉ trả về text)

Lưu ý MiMo-specific:
- Khi model sinh thinking block, PHẢI pass toàn bộ content (kể cả thinking)
  trở lại API trong multi-turn. Nếu không sẽ gặp lỗi 400
  "reasoning_content in thinking mode must be passed back"

Sentinel cho tool-status events trong stream_chat:
    chunk bắt đầu bằng TOOL_STATUS_PREFIX → chat_service chuyển thành status event
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Sentinel: stream_chat yields string này → chat_service chuyển thành status event
TOOL_STATUS_PREFIX = "\x00STATUS:"

_MAX_TOOL_ITERATIONS = 3


@dataclass
class _ToolCall:
    id: str
    name: str
    input_json: str = field(default="")

    def parsed_input(self) -> dict[str, Any]:
        try:
            return json.loads(self.input_json) if self.input_json else {}
        except json.JSONDecodeError:
            return {}

    def to_block(self) -> dict[str, Any]:
        return {
            "type": "tool_use",
            "id": self.id,
            "name": self.name,
            "input": self.parsed_input(),
        }


@dataclass
class _ToolUseEvent:
    """Phát từ _sse_stream khi stream kết thúc với stop_reason=tool_use.
    Chứa toàn bộ content blocks (kể cả thinking) để pass trở lại API.
    """
    full_content: list[dict[str, Any]]
    tool_calls: list[_ToolCall]


@dataclass
class _XmlArtifactEvent:
    """Sentinel từ _stream_text_filtered khi phát hiện <tool_call> XML artifact.
    Không có thêm text nào được yield sau event này.
    """


def _extract_text(content: list[dict[str, Any]]) -> str:
    """Lấy text từ Anthropic content array (bỏ thinking blocks)."""
    parts = []
    for block in content:
        if block.get("type") == "text":
            text = block.get("text", "")
            if text:
                parts.append(text)
    return "".join(parts).strip()


def _has_xml_tool_artifact(text: str) -> bool:
    return "<tool_call" in text.lower() or "</tool_call" in text.lower()


def _strip_xml_tool_artifacts(text: str) -> str:
    cleaned = re.sub(r"<\s*tool_call\s*>.*?</\s*tool_call\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<\s*tool_call\s*>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"</\s*tool_call\s*>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _split_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Tách system messages → system string + conversation list."""
    system_parts: list[str] = []
    conversation: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if content:
                system_parts.append(str(content))
        else:
            conversation.append(msg)
    return "\n\n".join(system_parts), conversation


def _normalize_conversation(conv: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Anthropic yêu cầu user/assistant xen kẽ, bắt đầu bằng user.
    - Thêm user stub nếu message đầu là assistant.
    - Merge consecutive same-role string messages.
    - Không merge nếu content là list (tool_use / tool_result blocks).
    """
    if not conv:
        return []

    result: list[dict[str, Any]] = []
    if conv[0].get("role") == "assistant":
        result.append({"role": "user", "content": "..."})

    for msg in conv:
        if result and result[-1].get("role") == msg.get("role"):
            prev = result[-1]
            prev_c = prev.get("content", "")
            curr_c = msg.get("content", "")
            if isinstance(prev_c, str) and isinstance(curr_c, str):
                prev["content"] = f"{prev_c}\n{curr_c}".strip()
            else:
                result.append(msg)
        else:
            result.append(msg)
    return result


class MimoProvider(LLMProvider):
    """LLM provider dùng MiMo Anthropic-compatible API (/anthropic/v1/messages)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    # ─── endpoint & headers ───────────────────────────────────────────────────

    @property
    def _endpoint(self) -> str:
        return f"{self.settings.mimo_anthropic_base_url.rstrip('/')}/messages"

    def _headers(self) -> dict[str, str]:
        api_key = self.settings.mimo_api_key.strip()
        if not api_key:
            raise RuntimeError("MIMO_API_KEY chưa được cấu hình.")
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    # ─── tools ────────────────────────────────────────────────────────────────

    def _web_search_tool_def(self, web_search_enabled: bool = True) -> dict[str, Any] | None:
        if not web_search_enabled or not self.settings.enable_web_search:
            return None
        return {
            "name": "web_search",
            "description": (
                "Tìm kiếm thông tin trên internet. "
                "Dùng khi không có đủ thông tin trong knowledge base, "
                "hoặc câu hỏi về sự kiện/thông báo mới nhất ngoài tầm dữ liệu."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm. Ưu tiên tiếng Việt cho thông tin UIT.",
                    }
                },
                "required": ["query"],
            },
        }

    def _get_tools(self, web_search_enabled: bool = True) -> list[dict[str, Any]]:
        tool = self._web_search_tool_def(web_search_enabled)
        return [tool] if tool else []

    # ─── payload builder ──────────────────────────────────────────────────────

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        stream: bool,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        system_prompt, conversation = _split_messages(messages)
        conversation = _normalize_conversation(conversation)

        payload: dict[str, Any] = {
            "model": self.settings.mimo_chat_model,
            "max_tokens": self.settings.mimo_max_completion_tokens,
            "stream": stream,
            "messages": conversation or [{"role": "user", "content": "Xin chào"}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = {"type": "auto"}
        return payload

    # ─── tool execution ───────────────────────────────────────────────────────

    async def _execute_tool(
        self,
        name: str,
        tool_input: dict[str, Any],
        *,
        web_search_max_results: int | None = None,
    ) -> str:
        if name == "web_search":
            query = tool_input.get("query", "")
            max_results = web_search_max_results or self.settings.web_search_max_results
            logger.info("[mimo] web_search query: %s", query)
            try:
                from app.services.web_search_service import WebSearchService
                return await WebSearchService().search(query, max_results=max_results)
            except Exception as exc:
                logger.warning("[mimo] web_search thất bại: %s", exc)
                return f"Không tìm kiếm được: {exc}"
        logger.warning("[mimo] tool không được hỗ trợ: %s", name)
        return (
            "Tool này không được hỗ trợ. Hãy tổng hợp câu trả lời từ thông tin đã có, "
            "không cần gọi thêm tool."
        )

    async def _apply_tool_calls(
        self,
        current_messages: list[dict[str, Any]],
        full_assistant_content: list[dict[str, Any]],
        tool_calls: list[_ToolCall],
        *,
        web_search_max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Thực thi tool calls, thêm assistant + user messages vào conversation.

        QUAN TRỌNG: full_assistant_content phải bao gồm cả thinking blocks
        (không chỉ tool_use) vì MiMo yêu cầu pass lại toàn bộ reasoning_content.
        """
        tool_results = []
        for tc in tool_calls:
            result = await self._execute_tool(tc.name, tc.parsed_input(), web_search_max_results=web_search_max_results)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })
        return current_messages + [
            {"role": "assistant", "content": full_assistant_content},
            {"role": "user", "content": tool_results},
        ]

    # ─── non-streaming chat (agentic loop) ────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> str:
        tools = self._get_tools(web_search_enabled)
        current: list[dict[str, Any]] = list(messages)  # type: ignore[assignment]
        timeout = httpx.Timeout(float(self.settings.mimo_timeout_seconds), connect=20.0)

        for iteration in range(_MAX_TOOL_ITERATIONS):
            # Luôn pass tools để model không sinh XML tool_call khi muốn gọi lại
            payload = self._build_payload(current, stream=False, tools=tools or None)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self._endpoint, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()

            content: list[dict[str, Any]] = data.get("content", [])
            stop_reason: str = data.get("stop_reason", "end_turn")

            if stop_reason != "tool_use":
                text = _extract_text(content)
                if _has_xml_tool_artifact(text):
                    logger.warning("[mimo] XML tool_call artifact in non-stream chat, triggering synthesis")
                    synthesized = await self._synthesize_after_xml_artifact(current, timeout)
                    return synthesized or _strip_xml_tool_artifacts(text)
                return text

            tool_calls = [
                _ToolCall(
                    id=blk["id"],
                    name=blk["name"],
                    input_json=json.dumps(blk.get("input", {})),
                )
                for blk in content
                if blk.get("type") == "tool_use"
            ]
            if not tool_calls:
                return _extract_text(content)

            logger.info("[mimo] chat tool use iteration %d: %s", iteration, [tc.name for tc in tool_calls])
            # Pass full_assistant_content (kể cả thinking) để MiMo không lỗi 400
            current = await self._apply_tool_calls(
                current, content, tool_calls, web_search_max_results=web_search_max_results
            )

        # Vượt quá max iterations → call lần cuối không tools
        payload = self._build_payload(current, stream=False)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self._endpoint, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
        text = _extract_text(data.get("content", []))
        if _has_xml_tool_artifact(text):
            logger.warning("[mimo] XML tool_call artifact in final non-stream chat")
            text = _strip_xml_tool_artifacts(text)
        return text

    async def _synthesize_after_xml_artifact(self, messages: list[dict[str, Any]], timeout: httpx.Timeout) -> str:
        synthesis_messages = messages + [{
            "role": "user",
            "content": (
                "Hãy trả lời trực tiếp câu hỏi hiện tại bằng tiếng Việt dựa trên ngữ cảnh đã có. "
                "Không gọi công cụ, không viết XML, không viết <tool_call>."
            ),
        }]
        payload = self._build_payload(synthesis_messages, stream=False)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self._endpoint, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
        return _strip_xml_tool_artifacts(_extract_text(data.get("content", [])))

    # ─── streaming chat ───────────────────────────────────────────────────────

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        web_search_enabled: bool = True,
        web_search_max_results: int | None = None,
    ) -> AsyncIterator[str]:  # type: ignore[override]
        if not self.settings.enable_mimo_streaming:
            content = await self.chat(
                messages,
                web_search_enabled=web_search_enabled,
                web_search_max_results=web_search_max_results,
            )
            if content:
                yield content
            return

        tools = self._get_tools(web_search_enabled)
        current: list[dict[str, Any]] = list(messages)  # type: ignore[assignment]

        for iteration in range(_MAX_TOOL_ITERATIONS):
            tool_event: _ToolUseEvent | None = None
            xml_artifact_seen = False

            async for event in self._stream_text_filtered(current, tools=tools or None):
                if isinstance(event, str):
                    yield event
                elif isinstance(event, _ToolUseEvent):
                    tool_event = event
                elif isinstance(event, _XmlArtifactEvent):
                    xml_artifact_seen = True

            if tool_event is None:
                if xml_artifact_seen:
                    logger.warning("[mimo] XML tool_call artifact detected, triggering synthesis")
                    synthesis_msgs = current + [{
                        "role": "user",
                        "content": (
                            "Hãy tổng hợp và trả lời câu hỏi dựa trên thông tin đã tìm được. "
                            "Trả lời trực tiếp bằng tiếng Việt, không gọi thêm công cụ."
                        ),
                    }]
                    async for ev in self._stream_text_filtered(synthesis_msgs, tools=None):
                        if isinstance(ev, str):
                            yield ev
                return

            # Chỉ emit status cho các tool được hỗ trợ
            supported = [tc for tc in tool_event.tool_calls if tc.name == "web_search"]
            unsupported = [tc for tc in tool_event.tool_calls if tc.name != "web_search"]
            logger.info("[mimo] stream tool use iteration %d: supported=%s unsupported=%s",
                        iteration, [tc.name for tc in supported], [tc.name for tc in unsupported])

            if supported:
                query = supported[0].parsed_input().get("query", "")
                if query:
                    yield f"{TOOL_STATUS_PREFIX}web_search:{query[:80]}"

            if not supported and unsupported:
                # Tất cả tool calls đều unsupported → trigger synthesis ngay
                logger.warning("[mimo] tất cả tool calls đều không được hỗ trợ (%s), synthesizing",
                               [tc.name for tc in unsupported])
                current = await self._apply_tool_calls(
                    current,
                    tool_event.full_content,
                    tool_event.tool_calls,
                    web_search_max_results=web_search_max_results,
                )
                synthesis_msgs = current + [{
                    "role": "user",
                    "content": (
                        "Hãy tổng hợp và trả lời câu hỏi dựa trên thông tin đã tìm được. "
                        "Trả lời trực tiếp bằng tiếng Việt."
                    ),
                }]
                async for ev in self._stream_text_filtered(synthesis_msgs, tools=None):
                    if isinstance(ev, str):
                        yield ev
                return

            # Pass full_assistant_content để tránh lỗi 400 do thiếu thinking
            current = await self._apply_tool_calls(
                current,
                tool_event.full_content,
                tool_event.tool_calls,
                web_search_max_results=web_search_max_results,
            )

        # Vượt quá max iterations → thêm instruction để model tổng hợp kết quả
        final_messages = current + [{
            "role": "user",
            "content": (
                "Dựa trên các kết quả tìm kiếm ở trên, hãy tổng hợp và trả lời câu hỏi ban đầu. "
                "Không tìm kiếm thêm nữa."
            ),
        }]
        async for event in self._stream_text_filtered(final_messages, tools=None):
            if isinstance(event, str):
                yield event
            elif isinstance(event, _XmlArtifactEvent):
                logger.warning("[mimo] XML artifact in final synthesis, stopping stream")

    async def _stream_text_filtered(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str | _ToolUseEvent | _XmlArtifactEvent]:
        """
        Bọc _sse_stream với rolling-buffer để phát hiện <tool_call> XML artifacts
        ngay cả khi tag bị tách ra nhiều SSE events.

        Yields:
          str               → text chunk an toàn (đã qua buffer)
          _ToolUseEvent     → proper tool_use block từ model
          _XmlArtifactEvent → phát hiện XML artifact; không còn text nào được yield sau đây
        """
        SENTINEL = "<tool_call>"
        MAX_LOOKAHEAD = len(SENTINEL) - 1  # giữ tối đa 10 ký tự trong buffer

        pending = ""
        xml_seen = False

        async for event in self._sse_stream(messages, tools=tools):
            if isinstance(event, _ToolUseEvent):
                # Flush pending trước khi trả về tool event
                if pending and not xml_seen:
                    yield pending
                    pending = ""
                if not xml_seen:
                    yield event
                continue

            if xml_seen:
                continue

            pending += event
            lower = pending.lower()

            if SENTINEL in lower:
                xml_pos = lower.find(SENTINEL)
                if xml_pos > 0:
                    yield pending[:xml_pos]
                xml_seen = True
                pending = ""
                continue

            # Emit phần an toàn (giữ lại MAX_LOOKAHEAD ký tự cuối phòng partial match)
            if len(pending) > MAX_LOOKAHEAD:
                safe_end = len(pending) - MAX_LOOKAHEAD
                yield pending[:safe_end]
                pending = pending[safe_end:]

        if not xml_seen and pending:
            yield pending

        if xml_seen:
            yield _XmlArtifactEvent()

    async def _sse_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str | _ToolUseEvent]:
        """
        Yields:
          str           → text chunk (thinking blocks bị bỏ qua)
          _ToolUseEvent → khi stream kết thúc với stop_reason=tool_use
                          (bao gồm full_content để pass lại cho MiMo)
        """
        payload = self._build_payload(messages, stream=True, tools=tools)
        timeout = httpx.Timeout(None, connect=20.0)

        # Thu thập toàn bộ content blocks để pass lại khi có tool use
        all_content_blocks: dict[int, dict[str, Any]] = {}
        tool_calls: dict[int, _ToolCall] = {}
        current_block_type: dict[int, str] = {}

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", self._endpoint, headers=self._headers(), json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == ": PROCESSING":
                        continue
                    if line.startswith("event:"):
                        continue
                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break

                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    evt_type = evt.get("type", "")

                    if evt_type == "content_block_start":
                        blk = evt.get("content_block", {})
                        idx = evt.get("index", 0)
                        block_type = blk.get("type", "")
                        current_block_type[idx] = block_type

                        if block_type == "text":
                            all_content_blocks[idx] = {"type": "text", "text": ""}
                        elif block_type == "thinking":
                            all_content_blocks[idx] = {
                                "type": "thinking",
                                "thinking": blk.get("thinking", ""),
                                "signature": blk.get("signature", ""),
                            }
                        elif block_type == "tool_use":
                            tool_calls[idx] = _ToolCall(
                                id=blk.get("id", ""),
                                name=blk.get("name", ""),
                            )
                            all_content_blocks[idx] = {
                                "type": "tool_use",
                                "id": blk.get("id", ""),
                                "name": blk.get("name", ""),
                                "input": {},
                            }

                    elif evt_type == "content_block_delta":
                        idx = evt.get("index", 0)
                        delta = evt.get("delta", {})
                        delta_type = delta.get("type", "")

                        if delta_type == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                # Yield ngay lập tức (realtime)
                                yield text
                                if idx in all_content_blocks:
                                    all_content_blocks[idx]["text"] = (
                                        all_content_blocks[idx].get("text", "") + text
                                    )

                        elif delta_type == "thinking_delta":
                            if idx in all_content_blocks:
                                all_content_blocks[idx]["thinking"] = (
                                    all_content_blocks[idx].get("thinking", "")
                                    + delta.get("thinking", "")
                                )

                        elif delta_type == "input_json_delta" and idx in tool_calls:
                            partial = delta.get("partial_json", "")
                            tool_calls[idx].input_json += partial

                    elif evt_type == "content_block_stop":
                        idx = evt.get("index", 0)
                        # Cập nhật input vào all_content_blocks cho tool_use
                        if idx in tool_calls and idx in all_content_blocks:
                            all_content_blocks[idx]["input"] = tool_calls[idx].parsed_input()

                    elif evt_type == "message_delta":
                        stop_reason = evt.get("delta", {}).get("stop_reason", "")
                        if stop_reason == "tool_use" and tool_calls:
                            # Trả về _ToolUseEvent với full content (kể cả thinking)
                            full_content = [
                                all_content_blocks[i]
                                for i in sorted(all_content_blocks.keys())
                            ]
                            yield _ToolUseEvent(
                                full_content=full_content,
                                tool_calls=list(tool_calls.values()),
                            )
                            return

    # ─── health check ─────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        if not self.settings.mimo_api_key.strip():
            return {
                "provider": "mimo",
                "format": "anthropic",
                "configured": False,
                "model": self.settings.mimo_chat_model,
            }
        timeout = httpx.Timeout(20.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    self._endpoint,
                    headers=self._headers(),
                    json={
                        "model": self.settings.mimo_chat_model,
                        "max_tokens": 8,
                        "messages": [{"role": "user", "content": "ping"}],
                        "stream": False,
                    },
                )
                resp.raise_for_status()
        except Exception as exc:
            return {
                "provider": "mimo",
                "format": "anthropic",
                "configured": True,
                "model": self.settings.mimo_chat_model,
                "status": "error",
                "error": str(exc),
            }
        return {
            "provider": "mimo",
            "format": "anthropic",
            "configured": True,
            "model": self.settings.mimo_chat_model,
            "status": "ok",
        }
