from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.services.document_ingestion_service import DocumentIngestionService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_ingest_uploaded_text_file_creates_document_and_chunks(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    uploads_dir = tmp_path / "uploads" / "admin"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    sample_file = uploads_dir / "sample-guideline.txt"
    sample_file.write_text("Huong dan hoc vu UIT " * 80, encoding="utf-8")

    db = make_session()
    try:
        service = DocumentIngestionService()

        async def fake_embeddings(chunks: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in chunks]

        service.embedding_provider.embed = fake_embeddings  # type: ignore[method-assign]
        service.qdrant.upsert_chunk = lambda vector, payload: f"vec-{payload['document_id']}-{len(payload['content'])}"  # type: ignore[method-assign]
        service.qdrant.delete_document_vectors = lambda document_id: None  # type: ignore[method-assign]

        result = asyncio.run(
            service.ingest_uploaded_file(
                db,
                source_file=sample_file,
                title="Huong dan hoc vu moi",
                category_code="ACADEMIC",
                group_name="Hoc vu",
                tags=["uit", "hoc-vu"],
                is_official_uit=True,
                create_announcement=True,
            )
        )
        db.commit()

        assert result.document.id > 0
        assert result.chunk_count > 0
        assert result.document.group_name == "Hoc vu"
        assert result.document.vector_metadata["storage_path"].startswith("uploads/admin/")
    finally:
        db.close()
