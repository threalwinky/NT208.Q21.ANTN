from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.knowledge import CollectedDocument, DocumentChunk
from app.models.users import User
from app.schemas.admin import AdminUploadOut
from app.schemas.documents import DocumentChunkOut, DocumentDetailOut, DocumentOut
from app.services.data_paths import resolve_data_dir
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.qdrant_service import QdrantService
from app.services.queue_service import QueueService

router = APIRouter()

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx", ".txt", ".md"}


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return normalized or "tai-lieu"


def serialize_document(document: CollectedDocument) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        title=document.title,
        url=document.url,
        group_name=document.group_name,
        summary=document.summary,
        file_type=document.file_type,
        is_official_uit=document.is_official_uit,
        is_academic_related=document.is_academic_related,
        is_wellbeing_related=document.is_wellbeing_related,
        tags=document.tags or [],
        published_at=document.published_at,
        updated_source_at=document.updated_source_at,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    q: str | None = Query(default=None),
    group_name: str | None = Query(default=None),
    official_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DocumentOut]:
    query = db.query(CollectedDocument)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(CollectedDocument.title.ilike(pattern), CollectedDocument.summary.ilike(pattern), CollectedDocument.cleaned_content.ilike(pattern)))
    if group_name:
        query = query.filter(CollectedDocument.group_name == group_name)
    if official_only:
        query = query.filter(CollectedDocument.is_official_uit.is_(True))
    documents = query.order_by(CollectedDocument.updated_source_at.desc().nullslast(), CollectedDocument.id.desc()).limit(80).all()
    return [serialize_document(document) for document in documents]


@router.post("/upload", response_model=AdminUploadOut)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    category_code: str = Form("ANNOUNCEMENT"),
    group_name: str = Form("Tài liệu tự tải lên"),
    tags: str = Form(""),
    is_official_uit: bool = Form(True),
    create_announcement: bool = Form(False),
    published_at: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminUploadOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ PDF, ảnh, CSV, XLSX, TXT hoặc Markdown.")

    uploads_dir = resolve_data_dir() / "uploads" / "documents"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_path = uploads_dir / f"{timestamp}-{slugify(title)}{suffix}"
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


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentDetailOut:
    document = db.query(CollectedDocument).filter(CollectedDocument.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    base = serialize_document(document).model_dump()
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .limit(12)
        .all()
    )
    return DocumentDetailOut(
        **base,
        cleaned_content=document.cleaned_content,
        chunks=[DocumentChunkOut(id=item.id, chunk_index=item.chunk_index, content=item.content, char_count=item.char_count) for item in chunks],
    )


@router.post("/{document_id}/reindex")
def reindex_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    document = db.query(CollectedDocument).filter(CollectedDocument.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    QueueService().push_job("reindex_document", {"document_id": document.id})
    return {"success": True, "documentId": document.id}


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    document = db.query(CollectedDocument).filter(CollectedDocument.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    try:
        QdrantService().delete_document_vectors(document.id)
    except Exception:
        pass
    db.delete(document)
    db.commit()
    return {"deleted": True}
