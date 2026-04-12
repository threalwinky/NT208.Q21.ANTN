from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.knowledge import (
    Announcement,
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    CrawlerLog,
    CrawlStatus,
    DataSource,
    DocumentChunk,
)
from app.services.ollama_service import OllamaService
from app.services.qdrant_service import QdrantService
from app.services.text_utils import clean_text, content_hash, split_chunks


class CrawlerService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.ollama = OllamaService()
        self.qdrant = QdrantService()

    async def crawl_source(self, db: Session, source: DataSource) -> CrawlerLog:
        log = CrawlerLog(data_source_id=source.id, status=CrawlStatus.RUNNING, message=f"Đang crawl {source.name}")
        db.add(log)
        db.commit()
        db.refresh(log)

        total_urls = 0
        new_documents = 0
        updated_documents = 0
        error_count = 0
        processed_urls = 0
        skipped_urls = 0
        url_errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(
            timeout=self.settings.crawler_timeout_seconds,
            headers={"User-Agent": self.settings.crawler_user_agent},
            follow_redirects=True,
        ) as client:
            try:
                html = await self._fetch_html(client, source.base_url)
                soup = BeautifulSoup(html, "lxml")
                links: list[str] = []
                for tag in soup.select("a[href]"):
                    href = tag.get("href")
                    if not href:
                        continue
                    url = urljoin(source.base_url, href)
                    if urlparse(url).netloc.endswith(source.domain):
                        links.append(url)
                links = list(dict.fromkeys(links))[: self.settings.crawler_max_pages]
                total_urls = len(links) + 1
                urls_to_process = [source.base_url, *links]
                default_category = db.query(ContentCategory).filter(ContentCategory.code == "ANNOUNCEMENT").first()

                for url in urls_to_process:
                    try:
                        raw_content, file_type = await self._read_content(client, url)
                        cleaned_content = clean_text(raw_content)
                        processed_urls += 1
                        if len(cleaned_content) < 80:
                            skipped_urls += 1
                            continue
                        hash_value = content_hash(cleaned_content)
                        document = db.query(CollectedDocument).filter(CollectedDocument.url == url).first()

                        if document and document.content_hash == hash_value:
                            skipped_urls += 1
                            continue

                        if document is None:
                            document = CollectedDocument(
                                title=self._guess_title(url, cleaned_content),
                                url=url,
                                data_source_id=source.id,
                                category_id=default_category.id if default_category else None,
                                group_name="Thông báo tổng hợp",
                                published_at=datetime.now(timezone.utc),
                                updated_source_at=datetime.now(timezone.utc),
                                tags=["crawler", source.domain],
                                raw_content=raw_content,
                                cleaned_content=cleaned_content,
                                summary=cleaned_content[:280],
                                confidence_level=ConfidenceLevel.HIGH if source.is_official_uit else ConfidenceLevel.MEDIUM,
                                is_official_uit=source.is_official_uit,
                                is_wellbeing_related="tâm lý" in cleaned_content.lower(),
                                is_academic_related=True,
                                vector_metadata={"source": source.name},
                                content_hash=hash_value,
                                file_type=file_type,
                            )
                            db.add(document)
                            db.flush()
                            new_documents += 1
                        else:
                            document.title = self._guess_title(url, cleaned_content)
                            document.raw_content = raw_content
                            document.cleaned_content = cleaned_content
                            document.summary = cleaned_content[:280]
                            document.updated_source_at = datetime.now(timezone.utc)
                            document.content_hash = hash_value
                            document.file_type = file_type
                            updated_documents += 1

                        await self._sync_vectors(db, document)
                        self._sync_announcement(db, document)
                        db.commit()
                    except Exception as exc:
                        db.rollback()
                        error_count += 1
                        if len(url_errors) < 12:
                            url_errors.append({"url": url, "error": str(exc)})

                log.status = CrawlStatus.READY
                log.message = (
                    f"Crawl hoàn tất cho {source.name}: {new_documents} mới, "
                    f"{updated_documents} cập nhật, {skipped_urls} bỏ qua, {error_count} lỗi."
                )
            except Exception as exc:
                log.status = CrawlStatus.FAILED
                log.message = str(exc)
                error_count += 1
                if len(url_errors) < 12:
                    url_errors.append({"url": source.base_url, "error": str(exc)})

        log.total_urls = total_urls
        log.new_documents = new_documents
        log.updated_documents = updated_documents
        log.error_count = error_count
        log.detail_json = {
            "source_name": source.name,
            "processed_urls": processed_urls,
            "skipped_urls": skipped_urls,
            "sample_errors": url_errors,
        }
        db.commit()
        db.refresh(log)
        return log

    async def _fetch_html(self, client: httpx.AsyncClient, url: str) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    async def _read_content(self, client: httpx.AsyncClient, url: str) -> tuple[str, str]:
        if url.lower().endswith(".pdf"):
            response = await client.get(url)
            response.raise_for_status()
            reader = PdfReader(BytesIO(response.content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text, "pdf"

        html = await self._fetch_html(client, url)
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(" ", strip=True), "html"

    def _guess_title(self, url: str, cleaned_content: str) -> str:
        path = urlparse(url).path.strip("/").split("/")
        from_url = path[-1].replace("-", " ").replace("_", " ").strip() if path and path[-1] else ""
        return (from_url[:120] or cleaned_content[:120] or "Tài liệu UIT").strip()

    async def _sync_vectors(self, db: Session, document: CollectedDocument) -> None:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        try:
            self.qdrant.delete_document_vectors(document.id)
        except Exception:
            pass

        chunks = split_chunks(document.cleaned_content or "")
        if not chunks:
            return
        vectors = await self.ollama.create_embedding(chunks)

        for index, chunk in enumerate(chunks):
            vector = vectors[index] if isinstance(vectors, list) and index < len(vectors) else []
            vector_id = None
            if isinstance(vector, list) and vector:
                vector_id = self.qdrant.upsert_chunk(
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

    def _sync_announcement(self, db: Session, document: CollectedDocument) -> None:
        announcement = db.query(Announcement).filter(Announcement.url == document.url).first()
        if announcement is None:
            announcement = Announcement(
                title=document.title,
                short_description=document.summary,
                url=document.url,
                group_name=document.group_name or "Học vụ",
                is_featured=False,
                published_at=document.published_at,
                document_id=document.id,
                is_official_uit=document.is_official_uit,
                tags=document.tags or [],
            )
            db.add(announcement)
        else:
            announcement.title = document.title
            announcement.short_description = document.summary
            announcement.document_id = document.id
            announcement.tags = document.tags or []
