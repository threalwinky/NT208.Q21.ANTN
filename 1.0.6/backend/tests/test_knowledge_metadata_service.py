from __future__ import annotations

from datetime import datetime, timezone

from app.services.knowledge_metadata_service import KnowledgeMetadataService


def test_build_metadata_extracts_targeting_and_freshness() -> None:
    service = KnowledgeMetadataService()

    metadata = service.build_metadata(
        title="Quy định chuẩn đầu ra tiếng Anh cho chương trình tài năng năm học 2025-2026",
        text=(
            "Áp dụng từ 01/09/2025 đến 31/08/2026 cho khóa tuyển năm 2024. "
            "Sinh viên chương trình tài năng cần IELTS 5.5 hoặc chứng chỉ tương đương."
        ),
        tags=["ngoại ngữ", "CTTN"],
        published_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
        updated_source_at=datetime.now(timezone.utc),
        url="https://daa.uit.edu.vn/chuan-dau-ra-ngoai-ngu",
    )

    assert metadata["document_kind"] == "ENGLISH_REQUIREMENT"
    assert metadata["school_years"] == ["2025-2026"]
    assert metadata["applies_to_programs"] == ["honors"]
    assert metadata["applies_to_cohorts"] == ["2024"]
    assert metadata["freshness_bucket"] == "CURRENT"
    assert metadata["effective_from"] is not None
    assert metadata["effective_to"] is not None
