from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.knowledge import (
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    DataSource,
    Department,
    DocumentChunk,
    SourceType,
)
from app.services.rag_service import RagService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_documents(db):
    source = DataSource(
        name="DAA",
        base_url="https://daa.uit.edu.vn",
        domain="daa.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    category = ContentCategory(code="ACADEMIC", display_name="Học vụ")
    department = Department(name="Phòng Đào tạo Đại học")
    db.add_all([source, category, department])
    db.flush()

    target = CollectedDocument(
        title="Hướng dẫn xin giấy xác nhận sinh viên trực tuyến",
        url="https://daa.uit.edu.vn/giay-xac-nhan",
        data_source_id=source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Quy trình xin giấy xác nhận sinh viên qua cổng DAA.",
        cleaned_content="Sinh viên truy cập cổng đào tạo DAA, mở biểu mẫu giấy xác nhận, điền thông tin và gửi yêu cầu trực tuyến.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    distractor = CollectedDocument(
        title="Thông báo thay đổi ngân hàng nhận học bổng",
        url="https://student.uit.edu.vn/hoc-bong-ngan-hang",
        data_source_id=source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Thông báo cập nhật ngân hàng nhận học bổng cho sinh viên.",
        cleaned_content="Sinh viên cập nhật thông tin tài khoản ngân hàng để nhận học bổng đúng hạn.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    db.add_all([target, distractor])
    db.flush()

    db.add_all(
        [
            DocumentChunk(
                document_id=target.id,
                chunk_index=0,
                content=target.cleaned_content or "",
                char_count=len(target.cleaned_content or ""),
            ),
            DocumentChunk(
                document_id=distractor.id,
                chunk_index=0,
                content=distractor.cleaned_content or "",
                char_count=len(distractor.cleaned_content or ""),
            ),
        ]
    )
    db.commit()
    return target, distractor


def test_hybrid_retrieval_prioritizes_keyword_match() -> None:
    db = make_session()
    try:
        target, distractor = seed_documents(db)
        service = RagService()

        async def fake_embedding(_: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        service.ollama.create_embedding = fake_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: [  # type: ignore[method-assign]
            SimpleNamespace(payload={"document_id": distractor.id, "content": distractor.cleaned_content}, score=0.95),
            SimpleNamespace(payload={"document_id": target.id, "content": target.cleaned_content}, score=0.35),
        ]

        contexts = asyncio.run(service.retrieve(db, "Cách xin giấy xác nhận sinh viên?", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
        assert contexts[0].score >= contexts[1].score
    finally:
        db.close()


def test_retrieve_falls_back_to_lexical_search_when_embedding_fails() -> None:
    db = make_session()
    try:
        target, _ = seed_documents(db)
        service = RagService()

        async def broken_embedding(_: str) -> list[float]:
            raise RuntimeError("ollama unavailable")

        service.ollama.create_embedding = broken_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: []  # type: ignore[method-assign]

        contexts = asyncio.run(service.retrieve(db, "Mình cần xin giấy xác nhận sinh viên", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
    finally:
        db.close()
