from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin
from app.db.session import get_db
from app.models.knowledge import CrawlerLog, DataSource, FAQ, CollectedDocument
from app.models.wellbeing import SystemConfig
from app.schemas.admin import (
    AdminDocumentOut,
    AdminRuntimeOut,
    AdminUploadOut,
    CrawlerLogOut,
    DataSourceOut,
    UpdateConfigRequest,
    UpdateDataSourceRequest,
)
from app.services.data_paths import resolve_data_dir
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.knowledge_refresh_service import KnowledgeRefreshService
from app.services.queue_service import QueueService

router = APIRouter()

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx", ".txt", ".md"}


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return normalized or "tai-lieu"


@router.get("/overview")
def admin_overview(db: Session = Depends(get_db), _=Depends(require_admin)) -> dict:
    queue = QueueService()
    refresh_service = KnowledgeRefreshService()
    runtime = refresh_service.get_runtime(db)
    return {
        "totalSources": db.query(DataSource).count(),
        "totalDocuments": db.query(CollectedDocument).count(),
        "totalFaqs": db.query(FAQ).count(),
        "recentCrawlerRuns": db.query(CrawlerLog).count(),
        "queueSize": queue.size(),
        "refreshStatus": runtime.get("status", "IDLE"),
    }


@router.get("/sources", response_model=list[DataSourceOut])
def list_sources(db: Session = Depends(get_db), _=Depends(require_admin)) -> list[DataSourceOut]:
    items = db.query(DataSource).order_by(DataSource.id.asc()).all()
    return [
        DataSourceOut(
            id=item.id,
            name=item.name,
            base_url=item.base_url,
            domain=item.domain,
            source_type=item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type),
            is_enabled=item.is_enabled,
            is_official_uit=item.is_official_uit,
            crawl_interval_minutes=item.crawl_interval_minutes,
        )
        for item in items
    ]


@router.patch("/sources/{source_id}")
def update_source(
    source_id: int,
    payload: UpdateDataSourceRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> dict:
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguồn dữ liệu.")
    source.is_enabled = payload.is_enabled
    db.commit()
    return {"success": True, "isEnabled": source.is_enabled}


@router.post("/sources/{source_id}/crawl")
def run_crawl(
    source_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> dict:
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguồn dữ liệu.")
    QueueService().push_job("crawl_source", {"source_id": source.id})
    return {"success": True, "message": f"Đã đưa nguồn {source.name} vào hàng đợi crawl."}


@router.post("/reindex")
def reindex_all(db: Session = Depends(get_db), _=Depends(require_admin)) -> dict:
    QueueService().push_job("reindex_all", {})
    return {"success": True, "totalDocuments": db.query(CollectedDocument).count()}


@router.post("/knowledge-refresh")
def run_knowledge_refresh(db: Session = Depends(get_db), _=Depends(require_admin)) -> dict:
    QueueService().push_job("refresh_corpus", {"trigger": "manual-admin"})
    return {"success": True, "message": "Đã đưa tác vụ làm mới corpus vào hàng đợi."}


@router.get("/crawler-logs", response_model=list[CrawlerLogOut])
def list_crawler_logs(db: Session = Depends(get_db), _=Depends(require_admin)) -> list[CrawlerLogOut]:
    items = db.query(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(20).all()
    return [
        CrawlerLogOut(
            id=item.id,
            data_source_id=item.data_source_id,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            total_urls=item.total_urls,
            new_documents=item.new_documents,
            updated_documents=item.updated_documents,
            error_count=item.error_count,
            message=item.message,
            detail_json=item.detail_json,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.get("/runtime", response_model=AdminRuntimeOut)
def admin_runtime(db: Session = Depends(get_db), _=Depends(require_admin)) -> AdminRuntimeOut:
    refresh_service = KnowledgeRefreshService()
    return AdminRuntimeOut(
        queue_size=QueueService().size(),
        refresh_schedule=refresh_service.get_schedule(db),
        refresh_runtime=refresh_service.get_runtime(db),
    )


@router.get("/configs")
def list_configs(db: Session = Depends(get_db), _=Depends(require_admin)) -> list[dict]:
    items = db.query(SystemConfig).order_by(SystemConfig.key.asc()).all()
    return [{"id": item.id, "key": item.key, "value_json": item.value_json, "description": item.description} for item in items]


@router.put("/configs")
def upsert_config(
    payload: UpdateConfigRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> dict:
    config = db.query(SystemConfig).filter(SystemConfig.key == payload.key).first()
    if config is None:
        config = SystemConfig(key=payload.key, value_json=payload.value_json, description=payload.description)
        db.add(config)
    else:
        config.value_json = payload.value_json
        config.description = payload.description
    db.commit()
    return {"success": True}


@router.get("/manual-documents", response_model=list[AdminDocumentOut])
def list_manual_documents(db: Session = Depends(get_db), _=Depends(require_admin)) -> list[AdminDocumentOut]:
    manual_source = db.query(DataSource).filter(DataSource.domain == "studify.local").first()
    if manual_source is None:
        return []
    items = (
        db.query(CollectedDocument)
        .filter(CollectedDocument.data_source_id == manual_source.id)
        .order_by(CollectedDocument.updated_source_at.desc().nullslast(), CollectedDocument.id.desc())
        .limit(12)
        .all()
    )
    return [
        AdminDocumentOut(
            id=item.id,
            title=item.title,
            url=item.url,
            group_name=item.group_name,
            file_type=item.file_type,
            is_official_uit=item.is_official_uit,
            updated_source_at=item.updated_source_at,
            vector_metadata=item.vector_metadata,
        )
        for item in items
    ]


@router.post("/uploads", response_model=AdminUploadOut)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category_code: str = Form("ANNOUNCEMENT"),
    group_name: str = Form("Thông báo quản trị"),
    tags: str = Form(""),
    is_official_uit: bool = Form(True),
    create_announcement: bool = Form(False),
    published_at: str | None = Form(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> AdminUploadOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ PDF, ảnh, CSV, XLSX, TXT hoặc Markdown.")

    uploads_dir = resolve_data_dir() / "uploads" / "admin"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_name = f"{timestamp}-{slugify(title)}{suffix}"
    stored_path = uploads_dir / stored_name
    stored_path.write_bytes(await file.read())

    parsed_published_at = None
    if published_at:
        try:
            parsed_published_at = datetime.fromisoformat(published_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="published_at phải là ISO datetime hợp lệ.") from exc

    ingestion = await DocumentIngestionService().ingest_uploaded_file(
        db,
        source_file=stored_path,
        title=title,
        category_code=category_code.upper(),
        group_name=group_name,
        tags=[item.strip() for item in tags.split(",") if item.strip()],
        is_official_uit=is_official_uit,
        create_announcement=create_announcement,
        published_at=parsed_published_at,
    )
    db.commit()
    db.refresh(ingestion.document)
    return AdminUploadOut(
        document_id=ingestion.document.id,
        title=ingestion.document.title,
        status=ingestion.status,
        chunk_count=ingestion.chunk_count,
        used_ocr=ingestion.used_ocr,
        group_name=ingestion.document.group_name or group_name,
        file_type=ingestion.document.file_type or "text",
        is_official_uit=ingestion.document.is_official_uit,
        url=ingestion.document.url,
    )
