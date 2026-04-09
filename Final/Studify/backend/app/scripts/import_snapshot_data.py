from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.knowledge import (
    Announcement,
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    DataSource,
    Department,
    DocumentChunk,
)
from app.services.data_paths import resolve_data_dir
from app.services.ollama_service import OllamaService
from app.services.qdrant_service import QdrantService
from app.services.text_utils import content_hash, split_chunks


def infer_category_code(record: dict) -> str:
    haystack = f"{record.get('title', '')} {record.get('url', '')} {record.get('text', '')}".lower()
    if any(keyword in haystack for keyword in ["tam-ly", "sức khỏe tinh thần", "stress", "không gian chia sẻ"]):
        return "WELLBEING"
    if any(keyword in haystack for keyword in ["học bổng", "hoc-bong"]):
        return "SCHOLARSHIP"
    if any(keyword in haystack for keyword in ["học phí", "hoc-phi", "tuition"]):
        return "TUITION"
    if any(keyword in haystack for keyword in ["lịch thi", "lich-thi", "exam"]):
        return "EXAM"
    if any(keyword in haystack for keyword in ["thông báo", "thong-bao", "tin tức", "announcement"]):
        return "ANNOUNCEMENT"
    if any(keyword in haystack for keyword in ["giấy xác nhận", "thủ tục", "huong-dan", "sinhvien", "hoc-vu", "tot-nghiep"]):
        return "ACADEMIC"
    return "OTHER"


def is_announcement(record: dict) -> bool:
    haystack = f"{record.get('title', '')} {record.get('url', '')}".lower()
    return any(keyword in haystack for keyword in ["thông báo", "thong-bao", "announcement", "tin tức", "tin-tuc"])


async def import_snapshot_records(db: Session, jsonl_path: Path | None = None) -> dict:
    data_dir = resolve_data_dir()
    records_path = jsonl_path or (data_dir / "processed" / "uit_documents.jsonl")
    if not records_path.exists():
        return {"imported": 0, "updated": 0, "skipped": 0, "message": f"Không tìm thấy {records_path}"}

    ollama = OllamaService()
    qdrant = QdrantService()
    category_map = {item.code: item for item in db.query(ContentCategory).all()}
    source_map = {item.base_url: item for item in db.query(DataSource).all()}
    imported = 0
    updated = 0
    skipped = 0

    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        url = record["url"]
        text = record.get("text", "")
        if len(text) < 120:
            skipped += 1
            continue

        source = source_map.get(record.get("base_url", ""))  # not always present
        if source is None:
            source = (
                db.query(DataSource)
                .filter(DataSource.name == record.get("source_name"))
                .first()
            )

        category_code = infer_category_code(record)
        category = category_map.get(category_code)
        existing = db.query(CollectedDocument).filter(CollectedDocument.url == url).first()
        hash_value = content_hash(text)

        if existing and existing.content_hash == hash_value:
            skipped += 1
            continue

        document = existing or CollectedDocument(
            title=record["title"],
            url=url,
        )
        document.title = record["title"]
        document.data_source_id = source.id if source else None
        document.category_id = category.id if category else None
        document.group_name = category.display_name if category else "Tài liệu UIT"
        document.tags = record.get("tags", [])
        document.raw_content = text
        document.cleaned_content = text
        document.summary = record.get("summary") or text[:400]
        document.confidence_level = ConfidenceLevel.HIGH if record.get("is_official_uit") else ConfidenceLevel.MEDIUM
        document.is_official_uit = bool(record.get("is_official_uit"))
        document.is_wellbeing_related = category_code == "WELLBEING"
        document.is_academic_related = category_code in {"ACADEMIC", "ANNOUNCEMENT", "EXAM", "TUITION", "SCHOLARSHIP"}
        document.vector_metadata = {
            "snapshot_file": record.get("snapshot_file"),
            "download_file": record.get("download_file"),
            "source_name": record.get("source_name"),
            "domain": record.get("domain"),
            "ocr_used": record.get("ocr_used", False),
        }
        document.content_hash = hash_value
        document.file_type = record.get("file_type", "markdown")

        if existing is None:
            db.add(document)
            db.flush()
            imported += 1
        else:
            updated += 1

        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        try:
            qdrant.delete_document_vectors(document.id)
        except Exception:
            pass

        chunks = split_chunks(text)
        if chunks:
            vectors = await ollama.create_embedding(chunks)
            for index, chunk in enumerate(chunks):
                vector = vectors[index] if isinstance(vectors, list) and index < len(vectors) else []
                vector_id = None
                if isinstance(vector, list) and vector:
                    vector_id = qdrant.upsert_chunk(
                        vector,
                        {
                            "document_id": document.id,
                            "title": document.title,
                            "content": chunk,
                            "url": document.url,
                            "is_official_uit": document.is_official_uit,
                        },
                    )
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk,
                        vector_id=vector_id,
                        char_count=len(chunk),
                    )
                )

        announcement = db.query(Announcement).filter(Announcement.url == document.url).first()
        if is_announcement(record):
            if announcement is None:
                announcement = Announcement(
                    title=document.title,
                    short_description=document.summary,
                    url=document.url,
                    group_name=document.group_name or "Thông báo",
                    document_id=document.id,
                    is_official_uit=document.is_official_uit,
                    tags=document.tags or [],
                )
                db.add(announcement)
            else:
                announcement.title = document.title
                announcement.short_description = document.summary
                announcement.document_id = document.id
                announcement.group_name = document.group_name or announcement.group_name
                announcement.tags = document.tags or []

        db.commit()

    return {"imported": imported, "updated": updated, "skipped": skipped, "message": "Đã nhập snapshot UIT vào knowledge base"}


async def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = await import_snapshot_records(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
