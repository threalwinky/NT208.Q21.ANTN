from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.knowledge import (
    Announcement,
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    ContentCategoryCode,
    DataSource,
    DocumentChunk,
    SourceType,
)
from app.services.data_paths import resolve_data_dir
from app.services.knowledge_metadata_service import KnowledgeMetadataService
from app.services.file_extraction_service import FileExtractionService
from app.services.ollama_service import OllamaService
from app.services.qdrant_service import QdrantService
from app.services.structured_facts_service import StructuredFactsService
from app.services.text_utils import clean_text, content_hash, split_chunks


@dataclass(slots=True)
class IngestionResult:
    document: CollectedDocument
    status: str
    chunk_count: int
    used_ocr: bool


class DocumentIngestionService:
    def __init__(self) -> None:
        self.ollama = OllamaService()
        self.qdrant = QdrantService()
        self.extractor = FileExtractionService()
        self.metadata = KnowledgeMetadataService()
        self.facts = StructuredFactsService()

    def ensure_manual_source(self, db: Session) -> DataSource:
        source = db.query(DataSource).filter(DataSource.domain == "studify.local").first()
        if source is None:
            source = DataSource(
                name="Admin Upload",
                base_url="https://studify.local/admin-upload",
                domain="studify.local",
                source_type=SourceType.REFERENCE,
                description="Nguồn tài liệu được quản trị tải thủ công vào Studify.",
                is_enabled=True,
                is_official_uit=False,
                crawl_interval_minutes=10080,
            )
            db.add(source)
            db.flush()
        return source

    def resolve_category(self, db: Session, category_code: str | None) -> ContentCategory | None:
        normalized = (category_code or ContentCategoryCode.OTHER.value).upper()
        category = db.query(ContentCategory).filter(ContentCategory.code == normalized).first()
        if category is None:
            display_name = {
                ContentCategoryCode.ACADEMIC.value: "Học vụ",
                ContentCategoryCode.ANNOUNCEMENT.value: "Thông báo",
                ContentCategoryCode.SCHOLARSHIP.value: "Học bổng",
                ContentCategoryCode.TUITION.value: "Học phí",
                ContentCategoryCode.WELLBEING.value: "Đồng hành",
                ContentCategoryCode.SKILL.value: "Kỹ năng",
                ContentCategoryCode.PROCEDURE.value: "Thủ tục",
            }.get(normalized, "Tài liệu khác")
            category = ContentCategory(code=normalized, display_name=display_name)
            db.add(category)
            db.flush()
        return category

    async def upsert_document(
        self,
        db: Session,
        *,
        title: str,
        url: str,
        text: str,
        source: DataSource | None,
        category_code: str,
        group_name: str,
        tags: list[str],
        file_type: str,
        is_official_uit: bool,
        published_at: datetime | None = None,
        vector_metadata: dict | None = None,
        create_announcement: bool = False,
    ) -> IngestionResult:
        cleaned_content = clean_text(text)
        if len(cleaned_content) < 80:
            raise ValueError("Nội dung tài liệu quá ngắn để đưa vào RAG.")

        category = self.resolve_category(db, category_code)
        hash_value = content_hash(cleaned_content)
        document = db.query(CollectedDocument).filter(CollectedDocument.url == url).first()
        status = "updated" if document else "created"

        if document and document.content_hash == hash_value:
            return IngestionResult(document=document, status="skipped", chunk_count=len(document.chunks), used_ocr=bool((vector_metadata or {}).get("ocr_used")))

        if document is None:
            document = CollectedDocument(title=title, url=url)
            db.add(document)
            db.flush()

        document.title = title
        document.url = url
        document.data_source_id = source.id if source else None
        document.category_id = category.id if category else None
        document.group_name = group_name
        document.published_at = published_at or document.published_at or datetime.now(timezone.utc)
        document.updated_source_at = datetime.now(timezone.utc)
        document.tags = tags
        document.raw_content = text
        document.cleaned_content = cleaned_content
        document.summary = cleaned_content[:420]
        document.confidence_level = ConfidenceLevel.HIGH if is_official_uit else ConfidenceLevel.MEDIUM
        document.is_official_uit = is_official_uit
        document.is_wellbeing_related = category_code == ContentCategoryCode.WELLBEING.value
        document.is_academic_related = category_code in {
            ContentCategoryCode.ACADEMIC.value,
            ContentCategoryCode.ANNOUNCEMENT.value,
            ContentCategoryCode.EXAM.value,
            ContentCategoryCode.TUITION.value,
            ContentCategoryCode.SCHOLARSHIP.value,
            ContentCategoryCode.PROCEDURE.value,
        }
        freshness_metadata = self.metadata.build_metadata(
            title=title,
            text=cleaned_content,
            tags=tags,
            published_at=document.published_at,
            updated_source_at=document.updated_source_at,
            url=url,
        )
        document.vector_metadata = {
            **(vector_metadata or {}),
            "freshness": freshness_metadata,
        }
        document.content_hash = hash_value
        document.file_type = file_type
        await self.sync_vectors(db, document)
        self.facts.sync_document_facts(db, document)
        if create_announcement:
            self.sync_announcement(db, document)
        db.flush()
        return IngestionResult(document=document, status=status, chunk_count=len(document.chunks), used_ocr=bool((vector_metadata or {}).get("ocr_used")))

    async def sync_vectors(self, db: Session, document: CollectedDocument) -> None:
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
                        "school_years": ((document.vector_metadata or {}).get("freshness") or {}).get("school_years", []),
                        "applies_to_programs": ((document.vector_metadata or {}).get("freshness") or {}).get("applies_to_programs", []),
                        "applies_to_cohorts": ((document.vector_metadata or {}).get("freshness") or {}).get("applies_to_cohorts", []),
                        "document_kind": ((document.vector_metadata or {}).get("freshness") or {}).get("document_kind"),
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

    def sync_announcement(self, db: Session, document: CollectedDocument) -> None:
        announcement = db.query(Announcement).filter(Announcement.url == document.url).first()
        if announcement is None:
            announcement = Announcement(
                title=document.title,
                short_description=document.summary,
                url=document.url,
                group_name=document.group_name or "Thông báo",
                is_featured=False,
                published_at=document.published_at,
                document_id=document.id,
                is_official_uit=document.is_official_uit,
                tags=document.tags or [],
            )
            db.add(announcement)
            return
        announcement.title = document.title
        announcement.short_description = document.summary
        announcement.group_name = document.group_name or announcement.group_name
        announcement.document_id = document.id
        announcement.is_official_uit = document.is_official_uit
        announcement.tags = document.tags or []

    async def ingest_uploaded_file(
        self,
        db: Session,
        *,
        source_file: Path,
        title: str,
        category_code: str,
        group_name: str,
        tags: list[str],
        is_official_uit: bool,
        create_announcement: bool,
        published_at: datetime | None = None,
    ) -> IngestionResult:
        text, used_ocr, file_type = self.extractor.extract_text_from_path(source_file)
        manual_source = self.ensure_manual_source(db)
        relative_path = source_file.relative_to(resolve_data_dir())
        return await self.upsert_document(
            db,
            title=title,
            url=f"{manual_source.base_url.rstrip('/')}/{source_file.name}",
            text=text,
            source=manual_source,
            category_code=category_code,
            group_name=group_name,
            tags=tags,
            file_type=file_type,
            is_official_uit=is_official_uit,
            published_at=published_at,
            vector_metadata={
                "storage_path": str(relative_path),
                "ocr_used": used_ocr,
                "uploaded_from": "admin",
            },
            create_announcement=create_announcement,
        )
