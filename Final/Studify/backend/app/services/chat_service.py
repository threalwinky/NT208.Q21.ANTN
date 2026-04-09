from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.wellbeing import SystemConfig
from app.schemas.chat import ChatReply, CitationItem
from app.services.ollama_service import OllamaService
from app.services.query_classifier import QueryAnalysis, analyze_query
from app.services.rag_service import RagService, RetrievedContext


@dataclass
class PreparedTurn:
    analysis: QueryAnalysis
    contexts: list[RetrievedContext]
    citations: list[CitationItem]
    suggestions: list[str]
    messages: list[dict[str, str]]


class ChatService:
    def __init__(self) -> None:
        self.ollama = OllamaService()
        self.rag = RagService()

    def _system_prompt(self, db: Session, key: str, fallback: str) -> str:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            return str(config.value_json.get("prompt", fallback))
        return fallback

    def _category_guidance(self, category: str) -> str:
        if category == "WELLBEING":
            return (
                "Người dùng đang cần một giọng điệu đồng hành nhẹ. "
                "Hãy phản hồi ấm áp, tự nhiên, không lên lớp, không chẩn đoán. "
                "Ưu tiên lắng nghe, tóm lại ngắn điều người dùng đang vướng, rồi gợi ý 2-3 bước nhỏ có thể làm ngay."
            )
        if category == "ANNOUNCEMENT":
            return (
                "Người dùng đang hỏi theo kiểu cập nhật nhanh. "
                "Ưu tiên câu trả lời ngắn, chia ý rõ, nêu mốc thời gian và nhắc nếu thông tin có thể đã cũ."
            )
        if category == "ACADEMIC":
            return (
                "Người dùng đang hỏi học vụ hoặc thủ tục. "
                "Ưu tiên nguồn UIT chính thức, nêu quy trình theo từng bước, và chỉ rõ nơi cần liên hệ nếu có."
            )
        return (
            "Người dùng đang mở đầu một phiên chat chung. "
            "Giữ giọng thân thiện như một người bạn cùng trường và chủ động giúp họ làm rõ nhu cầu nếu câu hỏi còn rộng."
        )

    def _action_suggestions(self, category: str) -> list[str]:
        if category == "WELLBEING":
            return [
                "Nói thêm cho mình biết điều đang làm bạn nặng đầu nhất lúc này.",
                "Nếu muốn, mình có thể giúp bạn tách tuần này thành vài việc nhỏ dễ bắt đầu hơn.",
                "Bạn cũng có thể lưu một dòng ngắn ở mục Nhật ký để Studify nhìn nhịp năng lượng của bạn rõ hơn.",
            ]
        if category == "ACADEMIC":
            return [
                "Mở Trung tâm học vụ để xem thêm tài liệu liên quan.",
                "Lưu thông báo quan trọng để đọc lại sau.",
                "Nếu bạn đang bị nhiều deadline dồn, mình có thể giúp chia lại kế hoạch tuần ngay trong khung chat này.",
            ]
        if category == "ANNOUNCEMENT":
            return [
                "Lưu thông báo này để đọc lại sau.",
                "Nếu muốn, mình có thể tóm tắt tiếp các mốc quan trọng nhất trong tuần này.",
                "Bạn cũng có thể hỏi tiếp theo kiểu: còn hạn nào gần nhất hoặc thủ tục nào liên quan?",
            ]
        return [
            "Bạn có thể hỏi mình về học vụ, thông báo, lịch thi, học phí hoặc cách sắp lại tuần này.",
            "Nếu hôm nay bạn thấy hơi mệt, cứ nói thẳng tình trạng hiện tại, mình sẽ đổi cách hỗ trợ cho phù hợp.",
            "Nếu cần, mình có thể tóm tắt lại thành các bước ngắn để bạn dễ làm tiếp.",
        ]

    def _fallback_answer(self, category: str, contexts: list[RetrievedContext]) -> str:
        if contexts:
            snippets = []
            for item in contexts[:2]:
                source_text = (item.document.summary or item.excerpt or "").strip()
                normalized = " ".join(source_text.split())
                if len(normalized) > 220:
                    normalized = f"{normalized[:217]}..."
                snippets.append(f"- {item.document.title}: {normalized}")
            snippet_block = "\n".join(snippets)
            return (
                "Mình đang gặp trục trặc kết nối AI nên sẽ tóm tắt nhanh từ dữ liệu đã tìm được:\n\n"
                f"{snippet_block}\n\n"
                "Nếu cần, bạn gửi tiếp câu hỏi cụ thể hơn để mình lọc lại thông tin gọn hơn."
            )

        if category == "WELLBEING":
            return (
                "Mình đang gặp trục trặc kết nối AI nên chưa phản hồi sâu như bình thường. "
                "Nếu hôm nay bạn hơi mệt hoặc quá tải, thử nghỉ 5 phút, uống nước, rồi nói cho mình biết việc nào đang nặng đầu nhất để mình cùng tách nhỏ tiếp."
            )

        return (
            "Mình đang gặp trục trặc kết nối AI nên chưa tổng hợp trọn vẹn được. "
            "Bạn có thể gửi lại câu hỏi ngắn hơn hoặc mở mục Học vụ/Thông báo để xem nguồn UIT chính thức trước."
        )

    def _stream_text_chunks(self, content: str, words_per_chunk: int = 18) -> list[str]:
        words = content.split(" ")
        if len(words) <= words_per_chunk:
            return [content]

        chunks: list[str] = []
        current_words: list[str] = []
        for word in words:
            current_words.append(word)
            if len(current_words) >= words_per_chunk:
                chunks.append(" ".join(current_words).strip())
                current_words = []
        if current_words:
            chunks.append(" ".join(current_words).strip())
        return [chunk if index == 0 else f" {chunk}" for index, chunk in enumerate(chunks) if chunk]

    def _assistant_reply(
        self,
        session_id: int,
        analysis: QueryAnalysis,
        citations: list[CitationItem],
        suggestions: list[str],
        answer: str,
    ) -> ChatReply:
        return ChatReply(
            session_id=session_id,
            category=analysis.category,
            answer=answer,
            is_urgent=analysis.is_urgent,
            risk_score=analysis.risk_score,
            citations=citations,
            action_suggestions=suggestions,
        )

    def _save_assistant_message(
        self,
        db: Session,
        session: ChatSession,
        analysis: QueryAnalysis,
        answer: str,
    ) -> None:
        session.updated_at = datetime.now(timezone.utc)
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                category=analysis.category,
                content=answer,
                risk_score=analysis.risk_score,
                is_urgent=analysis.is_urgent,
            )
        )
        db.commit()

    def _save_user_message(
        self,
        db: Session,
        session: ChatSession,
        analysis: QueryAnalysis,
        content: str,
    ) -> None:
        session.updated_at = datetime.now(timezone.utc)
        db.add(
            ChatMessage(
                session_id=session.id,
                role="user",
                category=analysis.category,
                content=content,
                risk_score=analysis.risk_score,
                is_urgent=analysis.is_urgent,
            )
        )
        db.commit()

    async def _prepare_turn(
        self,
        db: Session,
        session: ChatSession,
        content: str,
        analysis: QueryAnalysis | None = None,
    ) -> PreparedTurn:
        analysis = analysis or analyze_query(content)
        contexts = await self.rag.retrieve(db, content)
        citations = [
            CitationItem(
                document_id=item.document.id,
                title=item.document.title,
                url=item.document.url,
                source_label="Nguồn UIT chính thức" if item.document.is_official_uit else "Nguồn tham khảo",
                confidence=item.document.confidence_level.value if hasattr(item.document.confidence_level, "value") else str(item.document.confidence_level),
                excerpt=item.excerpt,
                updated_at=item.document.updated_source_at,
            )
            for item in contexts
        ]

        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id.asc())
            .limit(12)
            .all()
        )

        system_prompt = self._system_prompt(
            db,
            "chat_system_prompt",
            (
                "Bạn là Studify, trợ lý đồng hành dành cho sinh viên UIT. "
                "Luôn trả lời bằng tiếng Việt tự nhiên, ngắn gọn, hữu ích. "
                "Ưu tiên thông tin chính thức từ UIT, không bịa nguồn, và nếu dữ liệu có thể cũ thì phải nói rõ. "
                "Chatbot này không có mode cố định; bạn phải tự nhận diện khi nào người dùng đang hỏi học vụ, thông báo, lên kế hoạch hay chỉ đang cần một lời đồng hành nhẹ. "
                "Ở các đoạn tâm sự, chỉ hỗ trợ ở mức đồng hành nhẹ, lắng nghe, gợi ý nghỉ ngắn, sắp xếp lại việc và khuyến khích tìm người hỗ trợ trong trường khi cần."
            ),
        )
        context_block = "\n\n".join(
            f"[Nguồn {index + 1}] {item.document.title}\nURL: {item.document.url}\nTrích đoạn: {item.excerpt}"
            for index, item in enumerate(contexts)
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "system", "content": self._category_guidance(analysis.category)})
        if context_block:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Sử dụng ngữ cảnh dưới đây để trả lời. "
                        "Nếu trích nguồn không chính thức UIT thì phải nói rõ đó là nguồn tham khảo.\n\n"
                        f"{context_block}"
                    ),
                }
            )
        for message in history:
            messages.append({"role": "assistant" if message.role == "assistant" else "user", "content": message.content})

        return PreparedTurn(
            analysis=analysis,
            contexts=contexts,
            citations=citations,
            suggestions=self._action_suggestions(analysis.category),
            messages=messages,
        )

    async def answer(self, db: Session, session: ChatSession, content: str) -> ChatReply:
        analysis = analyze_query(content)
        self._save_user_message(db, session, analysis, content)
        prepared = await self._prepare_turn(db, session, content, analysis)
        try:
            answer = await self.ollama.chat(prepared.messages)
        except Exception:
            answer = self._fallback_answer(prepared.analysis.category, prepared.contexts)

        self._save_assistant_message(db, session, prepared.analysis, answer)
        return self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, answer)

    async def stream_answer(self, db: Session, session: ChatSession, content: str) -> AsyncIterator[dict]:
        analysis = analyze_query(content)
        yield {
            "type": "meta",
            "session_id": session.id,
            "category": analysis.category,
            "is_urgent": analysis.is_urgent,
            "risk_score": analysis.risk_score,
            "citations": [],
            "action_suggestions": self._action_suggestions(analysis.category),
        }
        await asyncio.sleep(0)
        yield {"type": "status", "label": "Studify đang phân tích câu hỏi..."}
        await asyncio.sleep(0)
        self._save_user_message(db, session, analysis, content)
        yield {"type": "status", "label": "Studify đang tìm dữ liệu UIT phù hợp..."}
        prepared = await self._prepare_turn(db, session, content, analysis)
        await asyncio.sleep(0)
        yield {"type": "status", "label": "Studify đang soạn câu trả lời..."}

        answer_parts: list[str] = []
        try:
            async for chunk in self.ollama.stream_chat(prepared.messages):
                deltas = self._stream_text_chunks(chunk, words_per_chunk=14) if len(chunk.split()) > 18 else [chunk]
                for delta in deltas:
                    answer_parts.append(delta)
                    yield {"type": "chunk", "delta": delta}
        except Exception:
            if not answer_parts:
                fallback = self._fallback_answer(prepared.analysis.category, prepared.contexts)
                for chunk in self._stream_text_chunks(fallback):
                    answer_parts.append(chunk)
                    yield {"type": "chunk", "delta": chunk}

        answer = "".join(answer_parts).strip()
        if not answer:
            fallback = self._fallback_answer(prepared.analysis.category, prepared.contexts)
            for chunk in self._stream_text_chunks(fallback):
                answer_parts.append(chunk)
                yield {"type": "chunk", "delta": chunk}
            answer = "".join(answer_parts).strip()

        self._save_assistant_message(db, session, prepared.analysis, answer)
        reply = self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, answer)
        yield {"type": "done", **reply.model_dump(mode="json")}
