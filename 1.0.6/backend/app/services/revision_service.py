"""
Dịch vụ "Ôn tập" kiểu NotebookLM: sinh viên tải PDF cá nhân -> RAG -> hỏi đáp
CHỈ dựa trên tài liệu trong notebook đó.

Cô lập dữ liệu: dùng collection Qdrant RIÊNG "studify_revision" (không đụng corpus
UIT chính thức "studify_chunks"), và mọi truy vấn đều LỌC theo notebook_id để
không rò chéo giữa các notebook/sinh viên.
"""
from __future__ import annotations

import logging
from pathlib import Path

from qdrant_client.http import models as qmodels

from app.models.revision import NotebookDocument, RevisionDocStatus
from app.services.embeddings import get_embedding_provider
from app.services.file_extraction_service import FileExtractionService
from app.services.llm import get_llm_provider
from app.services.qdrant_service import QdrantService
from app.services.text_utils import split_chunks

logger = logging.getLogger(__name__)

REVISION_COLLECTION = "studify_revision"


class RevisionService:
    def __init__(self) -> None:
        self.qdrant = QdrantService(REVISION_COLLECTION)
        self.embeddings = get_embedding_provider()
        self.llm = get_llm_provider()
        self.extractor = FileExtractionService()

    def _notebook_filter(self, notebook_id: int) -> qmodels.Filter:
        return qmodels.Filter(
            must=[qmodels.FieldCondition(key="notebook_id", match=qmodels.MatchValue(value=notebook_id))]
        )

    async def ingest_pdf(self, document: NotebookDocument, file_path: Path) -> None:
        """Trích xuất PDF -> chunk -> embed -> upsert vào collection ôn tập.
        Cập nhật trạng thái tài liệu (caller tự commit)."""
        try:
            text, used_ocr, _kind = self.extractor.extract_text_from_path(file_path)
            text = (text or "").strip()
            if not text:
                document.status = RevisionDocStatus.FAILED.value
                document.error = "Không trích xuất được nội dung (PDF có thể là ảnh scan không OCR được)."
                return

            chunks = split_chunks(text)
            count = 0
            for index, chunk in enumerate(chunks):
                vector = await self.embeddings.embed(chunk)
                if not isinstance(vector, list) or not vector or isinstance(vector[0], list):
                    continue
                self.qdrant.upsert_chunk(
                    vector,  # type: ignore[arg-type]
                    {
                        "notebook_id": document.notebook_id,
                        "user_id": document.user_id,
                        "document_id": document.id,
                        "doc_title": document.title,
                        "chunk_index": index,
                        "text": chunk,
                    },
                )
                count += 1

            document.chunk_count = count
            document.char_count = len(text)
            document.used_ocr = used_ocr
            document.status = RevisionDocStatus.READY.value if count else RevisionDocStatus.FAILED.value
            if not count:
                document.error = "Không tạo được đoạn nội dung nào để học."
        except Exception as exc:  # noqa: BLE001
            logger.error("[revision] ingest thất bại doc=%s: %s", document.id, exc)
            document.status = RevisionDocStatus.FAILED.value
            document.error = f"Lỗi xử lý tài liệu: {exc}"

    async def answer(self, notebook_id: int, question: str, limit: int = 6) -> dict:
        """Hỏi đáp CHỈ trong phạm vi notebook (lọc notebook_id)."""
        query = (question or "").strip()
        if not query:
            return {"answer": "Bạn hãy nhập câu hỏi nhé.", "citations": []}

        vector = await self.embeddings.embed(query)
        points = self.qdrant.search(vector, limit=limit, query_filter=self._notebook_filter(notebook_id))  # type: ignore[arg-type]
        contexts = [
            {
                "doc_title": p.payload.get("doc_title", "Tài liệu"),
                "text": p.payload.get("text", ""),
            }
            for p in points
            if p.payload and p.payload.get("text")
        ]

        if not contexts:
            return {
                "answer": (
                    "Mình chưa thấy nội dung liên quan trong tài liệu bạn đã tải lên notebook này. "
                    "Bạn thử thêm tài liệu, hoặc đặt câu hỏi cụ thể hơn theo nội dung trong file nhé."
                ),
                "citations": [],
            }

        context_block = "\n\n".join(
            f"[Trích đoạn {i + 1}] (từ: {c['doc_title']})\n{c['text']}" for i, c in enumerate(contexts)
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là trợ lý ÔN TẬP của sinh viên. CHỈ trả lời dựa trên nội dung tài liệu sinh viên đã "
                    "tải lên ở dưới. Nếu thông tin không có trong tài liệu, hãy nói rõ là tài liệu chưa đề cập, "
                    "TUYỆT ĐỐI không bịa và không dùng kiến thức ngoài tài liệu. Trả lời bằng tiếng Việt, rõ ràng, "
                    "có thể trích lại đoạn liên quan để sinh viên dễ ôn."
                ),
            },
            {"role": "system", "content": f"NỘI DUNG TÀI LIỆU:\n\n{context_block}"},
            {"role": "user", "content": query},
        ]

        try:
            answer = await self.llm.chat(messages, web_search_enabled=False)
        except Exception as exc:  # noqa: BLE001
            logger.error("[revision] llm thất bại: %s", exc)
            answer = "Mình đang gặp trục trặc khi tạo câu trả lời. Bạn thử lại sau giây lát nhé."

        citations: list[dict] = []
        seen: set[str] = set()
        for c in contexts:
            title = c["doc_title"]
            if title in seen:
                continue
            seen.add(title)
            citations.append({"doc_title": title, "excerpt": (c["text"] or "")[:200]})

        return {"answer": answer, "citations": citations[:5]}

    def delete_document_vectors(self, document_id: int) -> None:
        self.qdrant.delete_document_vectors(document_id)

    def delete_notebook_vectors(self, notebook_id: int) -> None:
        self.qdrant.delete_notebook_vectors(notebook_id)
