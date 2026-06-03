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
from app.scripts import import_snapshot_data
from app.services.text_utils import content_hash


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


class FakeEmbeddingProvider:
    async def embed(self, chunks: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in chunks]


class FakeQdrantService:
    def delete_document_vectors(self, document_id: int) -> None:  # noqa: ARG002
        return None

    def upsert_chunk(self, vector: list[float], payload: dict) -> str:  # noqa: ARG002
        return f"vec-{payload['document_id']}-{len(payload['content'])}"


def test_import_snapshot_records_resumes_from_progress_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(import_snapshot_data, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    monkeypatch.setattr(import_snapshot_data, "QdrantService", FakeQdrantService)

    first_text = (
        "Quy định chuẩn đầu ra ngoại ngữ năm học 2025-2026 dành cho khóa tuyển năm 2024. "
        "Sinh viên chương trình chuẩn cần TOEIC 450 hoặc IELTS 4.5 trước khi xét tốt nghiệp. "
        "Thông tin này được công bố trên cổng học vụ UIT."
    )
    second_text = (
        "Thông báo thu học phí học kỳ 2 năm học 2025-2026. "
        "Đợt 1 đóng đến 22/02/2026, đợt 2 từ 16/03/2026 đến 17/05/2026. "
        "Sinh viên tra cứu tại cổng student.uit.edu.vn và cần hoàn tất đúng hạn."
    )
    records = [
        {
            "title": "Chuẩn đầu ra ngoại ngữ khóa 2024",
            "url": "https://daa.uit.edu.vn/a-chuan-dau-ra-ngoai-ngu",
            "text": first_text,
            "summary": "Khóa 2024 cần TOEIC 450 hoặc IELTS 4.5.",
            "tags": ["ngoại ngữ"],
            "source_name": "DAA",
            "base_url": "https://daa.uit.edu.vn",
            "domain": "daa.uit.edu.vn",
            "is_official_uit": True,
            "file_type": "markdown",
        },
        {
            "title": "Thông báo thu học phí HK2 2025-2026",
            "url": "https://daa.uit.edu.vn/b-thong-bao-hoc-phi",
            "text": second_text,
            "summary": "Hạn đóng học phí HK2 năm học 2025-2026.",
            "tags": ["học phí"],
            "source_name": "DAA",
            "base_url": "https://daa.uit.edu.vn",
            "domain": "daa.uit.edu.vn",
            "is_official_uit": True,
            "file_type": "markdown",
        },
    ]

    jsonl_path = tmp_path / "uit_documents.jsonl"
    jsonl_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )
    progress_path = tmp_path / "snapshot_import_progress.json"
    sorted_records = sorted(
        records,
        key=lambda record: (
            -import_snapshot_data.record_priority(record),
            record.get("source_name", ""),
            record.get("url", ""),
        ),
    )

    db = make_session()
    try:
        completed_record = sorted_records[0]
        pending_record = sorted_records[1]
        existing_document = CollectedDocument(
            title=completed_record["title"],
            url=completed_record["url"],
            summary=completed_record["summary"],
            cleaned_content=completed_record["text"],
            raw_content=completed_record["text"],
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
            content_hash=content_hash(completed_record["text"]),
            published_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
            updated_source_at=datetime.now(timezone.utc),
            file_type="markdown",
        )
        db.add(existing_document)
        db.commit()

        signature = import_snapshot_data.records_signature(jsonl_path, None)
        progress_path.write_text(
            json.dumps(
                {
                    "signature": signature,
                    "records_total": 2,
                    "last_completed_index": 0,
                    "imported": 1,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "completed": False,
                    "error_samples": [],
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        result = asyncio.run(
            import_snapshot_data.import_snapshot_records(
                db,
                jsonl_path,
                progress_path=progress_path,
            )
        )

        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        imported_documents = db.query(CollectedDocument).order_by(CollectedDocument.url.asc()).all()
        pending_document = (
            db.query(CollectedDocument)
            .filter(CollectedDocument.url == pending_record["url"])
            .first()
        )

        assert result["resumed_from_index"] == 1
        assert result["imported"] == 2
        assert result["failed"] == 0
        assert len(imported_documents) == 2
        assert pending_document is not None
        assert pending_document.vector_metadata["freshness"]["document_kind"] in {"TUITION", "ENGLISH_REQUIREMENT"}
        assert pending_document.facts
        assert progress["completed"] is True
        assert progress["last_completed_index"] == 1
    finally:
        db.close()
