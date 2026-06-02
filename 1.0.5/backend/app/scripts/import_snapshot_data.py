from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.knowledge import (
    Announcement,
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    ContentCategoryCode,
    DataSource,
    Department,
    DocumentChunk,
)
from app.services.data_paths import resolve_data_dir
from app.services.embeddings import get_embedding_provider
from app.services.knowledge_metadata_service import KnowledgeMetadataService
from app.services.qdrant_service import QdrantService
from app.services.structured_facts_service import StructuredFactsService
from app.services.text_utils import content_hash, split_chunks


def infer_category_code(record: dict) -> str:
    haystack = f"{record.get('title', '')} {record.get('url', '')} {record.get('text', '')}".lower()
    if any(keyword in haystack for keyword in ["tam-ly", "sức khỏe tinh thần", "stress", "không gian chia sẻ"]):
        return "WELLBEING"
    if any(keyword in haystack for keyword in ["học bổng", "hoc-bong"]):
        return "SCHOLARSHIP"
    if any(keyword in haystack for keyword in ["học phí", "hoc-phi", "tuition"]):
        return "TUITION"
    if any(keyword in haystack for keyword in ["lịch đkhp", "dkhp", "thời khóa biểu", "tkb", "kế hoạch đào tạo năm học", "ke-hoach-nam", "nghỉ hè", "hoc ky he"]):
        return "SCHEDULE"
    if any(keyword in haystack for keyword in ["lịch thi", "lich-thi", "exam"]):
        return "EXAM"
    if any(keyword in haystack for keyword in ["giấy xác nhận", "giấy giới thiệu", "giay-gioi-thieu", "bảo lưu", "bao-luu", "bảo lưu", "tạm ngưng", "tam-ngung", "thôi học", "thoi-hoc", "song-ngành", "công nhận tín chỉ", "cong nhan tin chi"]):
        return "PROCEDURE"
    if any(keyword in haystack for keyword in ["thông báo", "thong-bao", "tin tức", "announcement"]):
        return "ANNOUNCEMENT"
    if any(keyword in haystack for keyword in ["thủ tục", "huong-dan", "sinhvien", "hoc-vu", "tot-nghiep", "cảnh báo sinh viên", "canh bao sinh vien", "xử lý học vụ", "xu ly hoc vu"]):
        return "ACADEMIC"
    return "OTHER"


def is_announcement(record: dict) -> bool:
    haystack = f"{record.get('title', '')} {record.get('url', '')}".lower()
    return any(keyword in haystack for keyword in ["thông báo", "thong-bao", "announcement", "tin tức", "tin-tuc"])


def record_priority(record: dict) -> int:
    haystack = " ".join(
        [
            record.get("title", ""),
            record.get("url", ""),
            record.get("summary", ""),
            record.get("text", "")[:1200],
            " ".join(record.get("tags", [])),
        ]
    ).lower()

    score = 0
    if record.get("is_official_uit"):
        score += 40

    if any(
        keyword in haystack
        for keyword in [
            "ke-hoach-nam",
            "kế hoạch đào tạo năm học",
            "ke hoach dao tao nam hoc",
            "nghỉ hè",
            "nghi-he",
            "hoc ky he",
            "học kỳ hè",
        ]
    ):
        score += 120

    if any(
        keyword in haystack
        for keyword in [
            "học phí",
            "hoc phi",
            "thu hoc phi",
            "thu-hoc-phi",
            "mức thu học phí",
            "muc thu hoc phi",
            "gia hạn học phí",
            "gia han hoc phi",
            "khtc",
        ]
    ):
        score += 110

    if any(
        keyword in haystack
        for keyword in [
            "xét tốt nghiệp",
            "xet tot nghiep",
            "tốt nghiệp",
            "tot nghiep",
            "chuẩn đầu ra",
            "chuan dau ra",
            "ngoại ngữ",
            "ngoai ngu",
        ]
    ):
        score += 100

    if any(
        keyword in haystack
        for keyword in [
            "quy trình",
            "quy trinh",
            "thủ tục",
            "thu tuc",
            "giấy xác nhận",
            "giay xac nhan",
            "cảnh báo sinh viên",
            "canh bao sinh vien",
            "xử lý học vụ",
            "xu ly hoc vu",
        ]
    ):
        score += 90

    if any(
        keyword in haystack
        for keyword in [
            "đăng ký học phần",
            "dang ky hoc phan",
            "dkhp",
            "thời khóa biểu",
            "thoi khoa bieu",
            "lịch thi",
            "lich thi",
        ]
    ):
        score += 80

    if any(domain in haystack for domain in ["daa.uit.edu.vn", "student.uit.edu.vn", "khtc.uit.edu.vn"]):
        score += 20

    return score


def ensure_category(db: Session, category_map: dict[str, ContentCategory], code: str) -> ContentCategory | None:
    category = category_map.get(code)
    if category is not None:
        return category

    display_name = {
        ContentCategoryCode.ACADEMIC.value: "Học vụ",
        ContentCategoryCode.ANNOUNCEMENT.value: "Thông báo",
        ContentCategoryCode.SCHEDULE.value: "Lịch học vụ",
        ContentCategoryCode.EXAM.value: "Lịch thi",
        ContentCategoryCode.TUITION.value: "Học phí",
        ContentCategoryCode.SCHOLARSHIP.value: "Học bổng",
        ContentCategoryCode.WELLBEING.value: "Đồng hành",
        ContentCategoryCode.SKILL.value: "Kỹ năng",
        ContentCategoryCode.PROCEDURE.value: "Thủ tục",
        ContentCategoryCode.OTHER.value: "Tài liệu khác",
    }.get(code, "Tài liệu khác")
    category = ContentCategory(code=code, display_name=display_name)
    db.add(category)
    db.flush()
    category_map[code] = category
    return category


def default_progress_path(records_path: Path) -> Path:
    return records_path.parent / "snapshot_import_progress.json"


def records_signature(records_path: Path, limit: int | None = None) -> dict:
    stats = records_path.stat()
    return {
        "path": str(records_path),
        "size": stats.st_size,
        "mtime_ns": stats.st_mtime_ns,
        "limit": limit,
    }


def load_progress(progress_path: Path, signature: dict, reset_progress: bool) -> dict:
    if reset_progress or not progress_path.exists():
        return {
            "signature": signature,
            "last_completed_index": -1,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "completed": False,
            "error_samples": [],
        }

    try:
        payload = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "signature": signature,
            "last_completed_index": -1,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "completed": False,
            "error_samples": [],
        }

    if payload.get("signature") != signature:
        return {
            "signature": signature,
            "last_completed_index": -1,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "completed": False,
            "error_samples": [],
        }
    return payload


def save_progress(progress_path: Path, payload: dict) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def import_snapshot_records(
    db: Session,
    jsonl_path: Path | None = None,
    *,
    resume: bool = True,
    reset_progress: bool = False,
    limit: int | None = None,
    progress_path: Path | None = None,
) -> dict:
    data_dir = resolve_data_dir()
    records_path = jsonl_path or (data_dir / "processed" / "uit_documents.jsonl")
    if not records_path.exists():
        return {"imported": 0, "updated": 0, "skipped": 0, "message": f"Không tìm thấy {records_path}"}

    embedding_provider = get_embedding_provider()
    qdrant = QdrantService()
    metadata_service = KnowledgeMetadataService()
    facts_service = StructuredFactsService()
    category_map = {item.code: item for item in db.query(ContentCategory).all()}
    source_map = {item.base_url: item for item in db.query(DataSource).all()}
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records.sort(
        key=lambda record: (
            -record_priority(record),
            record.get("source_name", ""),
            record.get("url", ""),
        )
    )
    if limit is not None:
        records = records[:limit]

    signature = records_signature(records_path, limit)
    progress = load_progress(progress_path or default_progress_path(records_path), signature, reset_progress)
    if resume and progress.get("completed") and progress.get("last_completed_index", -1) >= len(records) - 1:
        return {
            "imported": progress.get("imported", 0),
            "updated": progress.get("updated", 0),
            "skipped": progress.get("skipped", 0),
            "failed": progress.get("failed", 0),
            "message": "Snapshot đã được import đầy đủ ở lần chạy trước.",
            "progress_file": str(progress_path or default_progress_path(records_path)),
            "resumed_from_index": progress.get("last_completed_index", -1),
        }

    start_index = progress.get("last_completed_index", -1) + 1 if resume else 0
    imported = progress.get("imported", 0) if resume else 0
    updated = progress.get("updated", 0) if resume else 0
    skipped = progress.get("skipped", 0) if resume else 0
    failed = progress.get("failed", 0) if resume else 0
    error_samples = list(progress.get("error_samples", [])) if resume else []
    state_file = progress_path or default_progress_path(records_path)
    started_at = progress.get("started_at") if resume and progress.get("started_at") else datetime.now(timezone.utc).isoformat()

    progress.update(
        {
            "signature": signature,
            "records_total": len(records),
            "started_at": started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed": False,
            "last_completed_index": start_index - 1,
        }
    )
    save_progress(state_file, progress)

    for index, record in enumerate(records):
        if index < start_index:
            continue
        url = record["url"]
        text = record.get("text", "")
        if len(text) < 120:
            skipped += 1
            progress.update(
                {
                    "imported": imported,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                    "last_completed_index": index,
                    "last_url": url,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            save_progress(state_file, progress)
            continue

        try:
            source = source_map.get(record.get("base_url", ""))  # not always present
            if source is None:
                source = (
                    db.query(DataSource)
                    .filter(DataSource.name == record.get("source_name"))
                    .first()
                )

            category_code = infer_category_code(record)
            category = ensure_category(db, category_map, category_code)
            hash_value = content_hash(text)
            existing = db.query(CollectedDocument).filter(CollectedDocument.url == url).first()

            if existing and existing.content_hash == hash_value:
                skipped += 1
                progress.update(
                    {
                        "imported": imported,
                        "updated": updated,
                        "skipped": skipped,
                        "failed": failed,
                        "last_completed_index": index,
                        "last_url": url,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                save_progress(state_file, progress)
                continue

            def apply_document_fields(document: CollectedDocument) -> None:
                document.title = record["title"]
                document.url = url
                document.data_source_id = source.id if source else None
                document.category_id = category.id if category else None
                document.group_name = category.display_name if category else "Tài liệu UIT"
                document.published_at = document.published_at or datetime.now(timezone.utc)
                document.updated_source_at = datetime.now(timezone.utc)
                document.tags = record.get("tags", [])
                document.raw_content = text
                document.cleaned_content = text
                document.summary = record.get("summary") or text[:400]
                document.confidence_level = (
                    ConfidenceLevel.HIGH if record.get("is_official_uit") else ConfidenceLevel.MEDIUM
                )
                document.is_official_uit = bool(record.get("is_official_uit"))
                document.is_wellbeing_related = category_code == "WELLBEING"
                document.is_academic_related = category_code in {
                    "ACADEMIC",
                    "ANNOUNCEMENT",
                    "SCHEDULE",
                    "EXAM",
                    "TUITION",
                    "SCHOLARSHIP",
                    "PROCEDURE",
                }
                freshness_metadata = metadata_service.build_metadata(
                    title=record["title"],
                    text=text,
                    tags=record.get("tags", []),
                    published_at=document.published_at,
                    updated_source_at=document.updated_source_at,
                    url=url,
                )
                document.vector_metadata = {
                    "snapshot_file": record.get("snapshot_file"),
                    "download_file": record.get("download_file"),
                    "source_name": record.get("source_name"),
                    "domain": record.get("domain"),
                    "ocr_used": record.get("ocr_used", False),
                    "freshness": freshness_metadata,
                }
                document.content_hash = hash_value
                document.file_type = record.get("file_type", "markdown")

            document = existing or CollectedDocument(title=record["title"], url=url)
            record_status = "updated" if existing is not None else "imported"
            apply_document_fields(document)
            if existing is None:
                db.add(document)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    document = db.query(CollectedDocument).filter(CollectedDocument.url == url).first()
                    if document is None:
                        raise
                    apply_document_fields(document)
                    record_status = "updated"
            else:
                record_status = "updated"

            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
            try:
                qdrant.delete_document_vectors(document.id)
            except Exception:
                pass

            chunks = split_chunks(text)
            if chunks:
                vectors = await embedding_provider.embed(chunks)
                freshness_payload = ((document.vector_metadata or {}).get("freshness") or {})
                for chunk_index, chunk in enumerate(chunks):
                    vector = vectors[chunk_index] if isinstance(vectors, list) and chunk_index < len(vectors) else []
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
                                "school_years": freshness_payload.get("school_years", []),
                                "applies_to_programs": freshness_payload.get("applies_to_programs", []),
                                "applies_to_cohorts": freshness_payload.get("applies_to_cohorts", []),
                                "document_kind": freshness_payload.get("document_kind"),
                            },
                        )
                    db.add(
                        DocumentChunk(
                            document_id=document.id,
                            chunk_index=chunk_index,
                            content=chunk,
                            vector_id=vector_id,
                            char_count=len(chunk),
                        )
                    )

            facts_service.sync_document_facts(db, document)

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
            if record_status == "imported":
                imported += 1
            else:
                updated += 1
        except Exception as exc:
            db.rollback()
            failed += 1
            if len(error_samples) < 25:
                error_samples.append({"index": index, "url": url, "error": str(exc)})

        progress.update(
            {
                "imported": imported,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "error_samples": error_samples,
                "last_completed_index": index,
                "last_url": url,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        save_progress(state_file, progress)

    progress.update(
        {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "error_samples": error_samples,
            "completed": True,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_progress(state_file, progress)

    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "message": "Đã nhập snapshot UIT vào knowledge base",
        "progress_file": str(state_file),
        "resumed_from_index": start_index,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import snapshot UIT vào knowledge base với khả năng resume.")
    parser.add_argument("--jsonl-path", default=None, help="Đường dẫn tới file JSONL snapshot.")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số record import trong lượt chạy này.")
    parser.add_argument("--no-resume", action="store_true", help="Không resume từ checkpoint cũ.")
    parser.add_argument("--reset-progress", action="store_true", help="Xóa checkpoint hiện tại trước khi import.")
    parser.add_argument("--progress-file", default=None, help="Đường dẫn file checkpoint tùy chỉnh.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    init_db()
    db = SessionLocal()
    try:
        result = await import_snapshot_records(
            db,
            Path(args.jsonl_path) if args.jsonl_path else None,
            resume=not args.no_resume,
            reset_progress=args.reset_progress,
            limit=args.limit,
            progress_path=Path(args.progress_file) if args.progress_file else None,
        )
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
