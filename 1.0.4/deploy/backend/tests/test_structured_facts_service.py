from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.knowledge import CollectedDocument, ConfidenceLevel, StructuredFactType
from app.services.structured_facts_service import StructuredFactsService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_sync_document_facts_and_search_match_query_context() -> None:
    db = make_session()
    try:
        document = CollectedDocument(
            title="Hướng dẫn chuẩn đầu ra ngoại ngữ khóa tuyển năm 2024",
            url="https://daa.uit.edu.vn/chuan-dau-ra-khoa-2024",
            summary="CTĐTr khóa tuyển năm 2024 cần TOEIC 450 hoặc IELTS 4.5.",
            cleaned_content=(
                "Theo hướng dẫn chuẩn đầu ra ngoại ngữ áp dụng năm học 2025-2026, "
                "sinh viên chương trình chuẩn khóa tuyển năm 2024 cần TOEIC 450 hoặc IELTS 4.5. "
                "Quy định này dùng để xét điều kiện ngoại ngữ trước tốt nghiệp."
            ),
            published_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
            updated_source_at=datetime.now(timezone.utc),
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
        )
        db.add(document)
        db.flush()

        service = StructuredFactsService()
        facts = service.sync_document_facts(db, document)
        db.commit()

        assert facts
        assert facts[0].fact_type == StructuredFactType.ENGLISH_REQUIREMENT
        assert facts[0].school_year == "2025-2026"
        assert facts[0].value_json["toeic_scores"] == ["450"]
        assert facts[0].value_json["ielts_scores"] == ["4.5"]
        assert "2024" in (facts[0].applies_to_cohorts or [])

        ranked = service.search_facts(
            db,
            "IELTS đầu ra khóa 2024 là bao nhiêu?",
            context_document_ids=[document.id],
            limit=3,
        )

        assert ranked
        assert ranked[0].fact.document_id == document.id
        assert ranked[0].fact.fact_type == StructuredFactType.ENGLISH_REQUIREMENT
        assert ranked[0].score > 0
    finally:
        db.close()
