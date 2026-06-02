from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.academic import Reminder
from app.models.knowledge import CollectedDocument, DataSource, DocumentChunk
from app.models.wellbeing import InAppNotification
from app.services.knowledge_refresh_service import KnowledgeRefreshService
from app.services.crawler_service import CrawlerService
from app.services.embeddings import get_embedding_provider
from app.services.qdrant_service import QdrantService
from app.services.queue_service import QueueService
from app.services.text_utils import split_chunks
from app.core.config import get_settings


async def process_job(job: dict) -> None:
    db: Session = SessionLocal()
    try:
        job_type = job.get("job_type")
        payload = job.get("payload", {})

        if job_type == "crawl_source":
            source = db.query(DataSource).filter(DataSource.id == payload.get("source_id")).first()
            if source and source.is_enabled:
                await CrawlerService().crawl_source(db, source)
        elif job_type == "reindex_all":
            embedding_provider = get_embedding_provider()
            qdrant = QdrantService()
            for document in db.query(CollectedDocument).all():
                db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
                try:
                    qdrant.delete_document_vectors(document.id)
                except Exception:
                    pass
                chunks = split_chunks(document.cleaned_content or "")
                vectors = await embedding_provider.embed(chunks) if chunks else []
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
                    db.add(DocumentChunk(document_id=document.id, chunk_index=index, content=chunk, vector_id=vector_id, char_count=len(chunk)))
        elif job_type == "reindex_document":
            document = db.query(CollectedDocument).filter(CollectedDocument.id == payload.get("document_id")).first()
            if document:
                embedding_provider = get_embedding_provider()
                qdrant = QdrantService()
                db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
                try:
                    qdrant.delete_document_vectors(document.id)
                except Exception:
                    pass
                chunks = split_chunks(document.cleaned_content or "")
                vectors = await embedding_provider.embed(chunks) if chunks else []
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
                    db.add(DocumentChunk(document_id=document.id, chunk_index=index, content=chunk, vector_id=vector_id, char_count=len(chunk)))
        elif job_type == "refresh_corpus":
            await KnowledgeRefreshService().run_refresh(db, trigger=str(payload.get("trigger", "manual")))
        db.commit()
    finally:
        db.close()


def dispatch_due_reminders() -> None:
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        reminders = (
            db.query(Reminder)
            .filter(Reminder.sent.is_(False), Reminder.remind_at <= now)
            .order_by(Reminder.remind_at.asc())
            .all()
        )
        for reminder in reminders:
            db.add(
                InAppNotification(
                    user_id=reminder.task.user_id,
                    title="Nhắc việc từ Studify",
                    content=reminder.message or f"Đến hạn việc: {reminder.task.title}",
                    action_link="/planner",
                )
            )
            reminder.sent = True
            reminder.last_sent_at = now
            if reminder.recurring_mode == "WEEKLY":
                reminder.sent = False
                reminder.remind_at = reminder.remind_at + timedelta(days=7)
        db.commit()
    finally:
        db.close()


async def main() -> None:
    init_db()
    settings = get_settings()
    queue = QueueService()
    refresh_service = KnowledgeRefreshService()
    last_reminder_scan = 0.0
    last_refresh_scan = 0.0
    while True:
        job = queue.pop_job(timeout=2)
        if job:
            try:
                await process_job(job)
            except Exception as exc:
                print(f"[worker] job failed: {exc}")
        current_time = time.time()
        if current_time - last_reminder_scan > 30:
            dispatch_due_reminders()
            last_reminder_scan = current_time
        if current_time - last_refresh_scan > settings.knowledge_refresh_poll_seconds:
            db: Session = SessionLocal()
            try:
                if refresh_service.should_queue_periodic_run(db):
                    refresh_service.mark_queued(db, trigger="scheduled-72h")
                    queue.push_job("refresh_corpus", {"trigger": "scheduled-72h"})
            finally:
                db.close()
            last_refresh_scan = current_time


if __name__ == "__main__":
    asyncio.run(main())
