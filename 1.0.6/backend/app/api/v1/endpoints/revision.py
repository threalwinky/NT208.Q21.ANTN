from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.revision import Notebook, NotebookDocument, RevisionDocStatus
from app.models.users import User
from app.schemas.revision import (
    AskRequest,
    AskResponse,
    NotebookCreate,
    NotebookDetailOut,
    NotebookDocumentOut,
    NotebookOut,
)
from app.services.data_paths import resolve_data_dir
from app.services.revision_service import RevisionService

router = APIRouter()

MAX_NOTEBOOKS_PER_USER = 30
MAX_DOCS_PER_NOTEBOOK = 25
MAX_UPLOAD_SIZE_MB = 25
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
_UPLOAD_CHUNK = 1024 * 1024


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return normalized[:60] or "tai-lieu"


def _doc_out(doc: NotebookDocument) -> NotebookDocumentOut:
    return NotebookDocumentOut(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        char_count=doc.char_count,
        used_ocr=doc.used_ocr,
        error=doc.error,
        created_at=doc.created_at,
    )


def _notebook_out(notebook: Notebook) -> NotebookOut:
    docs = notebook.documents
    return NotebookOut(
        id=notebook.id,
        title=notebook.title,
        document_count=len(docs),
        ready_count=sum(1 for d in docs if d.status == RevisionDocStatus.READY.value),
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
    )


def _get_owned_notebook(db: Session, user: User, notebook_id: int) -> Notebook:
    notebook = db.get(Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sổ ôn tập.")
    return notebook


# ─── Notebooks ────────────────────────────────────────────────────────────────


@router.get("/notebooks", response_model=list[NotebookOut])
def list_notebooks(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[NotebookOut]:
    notebooks = (
        db.query(Notebook)
        .filter(Notebook.user_id == user.id)
        .order_by(Notebook.updated_at.desc(), Notebook.id.desc())
        .all()
    )
    return [_notebook_out(nb) for nb in notebooks]


@router.post("/notebooks", response_model=NotebookOut)
def create_notebook(
    payload: NotebookCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotebookOut:
    total = db.scalar(select(func.count(Notebook.id)).where(Notebook.user_id == user.id)) or 0
    if total >= MAX_NOTEBOOKS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Bạn đã đạt giới hạn {MAX_NOTEBOOKS_PER_USER} sổ ôn tập.")
    notebook = Notebook(user_id=user.id, title=payload.title.strip())
    db.add(notebook)
    db.commit()
    db.refresh(notebook)
    return _notebook_out(notebook)


@router.get("/notebooks/{notebook_id}", response_model=NotebookDetailOut)
def get_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotebookDetailOut:
    notebook = _get_owned_notebook(db, user, notebook_id)
    docs = sorted(notebook.documents, key=lambda d: d.id, reverse=True)
    base = _notebook_out(notebook)
    return NotebookDetailOut(**base.model_dump(), documents=[_doc_out(d) for d in docs])


@router.delete("/notebooks/{notebook_id}", response_model=dict[str, bool])
def delete_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    notebook = _get_owned_notebook(db, user, notebook_id)
    # gỡ vector + file của toàn bộ tài liệu trong notebook
    RevisionService().delete_notebook_vectors(notebook.id)
    for doc in notebook.documents:
        _remove_file(doc.stored_path)
    db.delete(notebook)
    db.commit()
    return {"deleted": True}


# ─── Documents ──────────────────────────────────────────────────────────────


def _remove_file(stored_path: str | None) -> None:
    if not stored_path:
        return
    try:
        Path(stored_path).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass


@router.post("/notebooks/{notebook_id}/documents", response_model=NotebookDocumentOut)
async def upload_document(
    notebook_id: int,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotebookDocumentOut:
    notebook = _get_owned_notebook(db, user, notebook_id)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".pdf":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ tải lên file PDF.")

    current = db.scalar(
        select(func.count(NotebookDocument.id)).where(NotebookDocument.notebook_id == notebook.id)
    ) or 0
    if current >= MAX_DOCS_PER_NOTEBOOK:
        raise HTTPException(status_code=400, detail=f"Mỗi sổ tối đa {MAX_DOCS_PER_NOTEBOOK} tài liệu.")

    uploads_dir = resolve_data_dir() / "revision" / str(user.id) / str(notebook.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    display_title = (title or "").strip() or Path(file.filename or "Tài liệu").stem
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    stored_path = uploads_dir / f"{timestamp}-{_slugify(display_title)}.pdf"

    total_bytes = 0
    try:
        with stored_path.open("wb") as buffer:
            while chunk := await file.read(_UPLOAD_CHUNK):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    stored_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"File vượt quá giới hạn {MAX_UPLOAD_SIZE_MB} MB.")
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Không thể lưu file tải lên.") from exc

    if total_bytes == 0:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File tải lên rỗng.")

    document = NotebookDocument(
        notebook_id=notebook.id,
        user_id=user.id,
        title=display_title[:255],
        filename=(file.filename or "tai-lieu.pdf")[:255],
        stored_path=str(stored_path),
        status=RevisionDocStatus.PROCESSING.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Trích xuất + embed + index ngay (MVP làm inline; ingest tự cập nhật trạng thái).
    await RevisionService().ingest_pdf(document, stored_path)
    db.add(document)
    db.commit()
    db.refresh(document)
    return _doc_out(document)


@router.delete("/notebooks/{notebook_id}/documents/{document_id}", response_model=dict[str, bool])
def delete_document(
    notebook_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    notebook = _get_owned_notebook(db, user, notebook_id)
    document = db.get(NotebookDocument, document_id)
    if not document or document.notebook_id != notebook.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    RevisionService().delete_document_vectors(document.id)
    _remove_file(document.stored_path)
    db.delete(document)
    db.commit()
    return {"deleted": True}


# ─── Hỏi đáp (RAG scoped trong notebook) ─────────────────────────────────────


@router.post("/notebooks/{notebook_id}/ask", response_model=AskResponse)
async def ask_notebook(
    notebook_id: int,
    payload: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AskResponse:
    notebook = _get_owned_notebook(db, user, notebook_id)
    ready = [d for d in notebook.documents if d.status == RevisionDocStatus.READY.value]
    if not ready:
        return AskResponse(
            answer="Sổ này chưa có tài liệu nào sẵn sàng. Hãy tải lên một file PDF rồi hỏi lại nhé.",
            citations=[],
        )
    result = await RevisionService().answer(notebook.id, payload.question)
    return AskResponse(**result)
