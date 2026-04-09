from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin
from app.db.session import get_db
from app.models.knowledge import CrawlerLog, DataSource, FAQ, CollectedDocument
from app.models.wellbeing import SystemConfig
from app.schemas.admin import CrawlerLogOut, DataSourceOut, UpdateConfigRequest, UpdateDataSourceRequest
from app.services.queue_service import QueueService

router = APIRouter()


@router.get("/overview")
def admin_overview(db: Session = Depends(get_db), _=Depends(require_admin)) -> dict:
    return {
        "totalSources": db.query(DataSource).count(),
        "totalDocuments": db.query(CollectedDocument).count(),
        "totalFaqs": db.query(FAQ).count(),
        "recentCrawlerRuns": db.query(CrawlerLog).count(),
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
            created_at=item.created_at,
        )
        for item in items
    ]


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
