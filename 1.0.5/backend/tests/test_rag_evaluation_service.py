from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.knowledge import CollectedDocument, ConfidenceLevel
from app.services.rag_evaluation_service import RagEvaluationService
from app.services.rag_service import RetrievedContext
from app.services.structured_facts_service import StructuredFactsService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_evaluate_aggregates_retrieval_domain_and_fact_metrics(tmp_path: Path) -> None:
    db = make_session()
    try:
        document = CollectedDocument(
            title="Chuẩn đầu ra ngoại ngữ khóa tuyển năm 2024",
            url="https://daa.uit.edu.vn/chuan-dau-ra-ngoai-ngu-k2024",
            summary="Chương trình chuẩn khóa tuyển năm 2024 cần IELTS 4.5 hoặc TOEIC 450.",
            cleaned_content=(
                "Theo hướng dẫn chuẩn đầu ra ngoại ngữ năm học 2025-2026, "
                "sinh viên chương trình chuẩn khóa tuyển năm 2024 cần IELTS 4.5 hoặc TOEIC 450."
            ),
            published_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
            updated_source_at=datetime.now(timezone.utc),
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
        )
        db.add(document)
        db.flush()
        StructuredFactsService().sync_document_facts(db, document)
        db.commit()

        service = RagEvaluationService()

        async def fake_retrieve(db_session, query: str, limit: int = 5):  # noqa: ARG001
            return [RetrievedContext(document=document, excerpt=document.summary or "", score=0.97)]

        service.rag.retrieve = fake_retrieve  # type: ignore[method-assign]

        benchmark_file = tmp_path / "rag_suite.json"
        benchmark_file.write_text(
            json.dumps(
                [
                    {
                        "query": "Chuẩn tiếng Anh đầu ra của khóa 2024 là gì?",
                        "expected_category": "ACADEMIC",
                        "require_official": True,
                        "expected_keywords": ["chuẩn đầu ra", "ielts 4.5"],
                        "expected_domains": ["daa.uit.edu.vn"],
                        "expected_fact_types": ["ENGLISH_REQUIREMENT"],
                        "expected_school_years": ["2025-2026"],
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        result = asyncio.run(service.evaluate(db, benchmark_file, top_k=3))

        assert result["total_queries"] == 1
        assert result["metrics"]["classifier_hit_rate"] == 1.0
        assert result["metrics"]["retrieval_hit_rate"] == 1.0
        assert result["metrics"]["official_hit_rate"] == 1.0
        assert result["metrics"]["domain_hit_rate"] == 1.0
        assert result["metrics"]["fact_hit_rate"] == 1.0
        assert result["metrics"]["mrr"] == 1.0
        assert result["failed_cases"] == []
    finally:
        db.close()
