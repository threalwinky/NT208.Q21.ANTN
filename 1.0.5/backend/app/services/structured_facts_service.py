from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge import (
    CollectedDocument,
    ConfidenceLevel,
    StructuredFactType,
    StructuredKnowledgeFact,
)
from app.services.knowledge_metadata_service import KnowledgeMetadataService


@dataclass(slots=True)
class RankedStructuredFact:
    fact: StructuredKnowledgeFact
    score: float


class StructuredFactsService:
    def __init__(self) -> None:
        self.metadata = KnowledgeMetadataService()

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
        stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        compact = re.sub(r"[^a-z0-9/.-]+", " ", stripped)
        return re.sub(r"\s+", " ", compact).strip()

    def _query_topics(self, text: str) -> set[str]:
        normalized = self._normalize(text)
        topics: set[str] = set()
        if any(token in normalized for token in ["ngoai ngu", "tieng anh", "toeic", "ielts", "vstep", "vnu ept", "chuan dau ra"]):
            topics.add(StructuredFactType.ENGLISH_REQUIREMENT.value)
        if any(token in normalized for token in ["hoc phi", "thu hoc phi", "gia han hoc phi", "mien giam hoc phi"]):
            topics.add(StructuredFactType.TUITION.value)
        if any(token in normalized for token in ["xet tot nghiep", "tot nghiep", "trao bang", "ra truong"]):
            topics.add(StructuredFactType.GRADUATION.value)
        if any(token in normalized for token in ["giay xac nhan", "giay gioi thieu", "thu tuc", "bao luu", "tam ngung", "thoi hoc"]):
            topics.add(StructuredFactType.PROCEDURE.value)
        if any(token in normalized for token in ["nghi he", "ke hoach nam", "khai giang", "tet am lich", "hoc ky he"]):
            topics.add(StructuredFactType.ANNUAL_PLAN.value)
        if any(token in normalized for token in ["canh bao hoc vu", "canh bao hoc tap", "canh bao sinh vien", "xu ly hoc vu"]):
            topics.add(StructuredFactType.ACADEMIC_WARNING.value)
        if any(token in normalized for token in ["dang ky hoc phan", "xac nhan dkhp", "dkhp"]):
            topics.add(StructuredFactType.REGISTRATION.value)
        if any(token in normalized for token in ["chuong trinh dao tao", "ctdt", "ke hoach hoc tap", "hoc mon nao"]):
            topics.add(StructuredFactType.CURRICULUM.value)
        if any(token in normalized for token in ["hoc bong", "kkht", "khuyen khich hoc tap"]):
            topics.add(StructuredFactType.SCHOLARSHIP.value)
        return topics

    def _fact_type_value(self, fact_type: StructuredFactType | str) -> str:
        return fact_type.value if hasattr(fact_type, "value") else str(fact_type)

    def _infer_fact_type(self, document: CollectedDocument) -> StructuredFactType:
        haystack = self._normalize(
            " ".join(
                filter(
                    None,
                    [
                        document.title,
                        document.url,
                        document.summary or "",
                        document.cleaned_content or "",
                    ],
                )
            )
        )
        if any(token in haystack for token in ["ngoai ngu", "tieng anh", "toeic", "ielts", "vstep", "vnu ept", "chuan dau ra"]):
            return StructuredFactType.ENGLISH_REQUIREMENT
        if any(token in haystack for token in ["hoc phi", "thu hoc phi", "muc thu hoc phi", "gia han hoc phi"]):
            return StructuredFactType.TUITION
        if any(token in haystack for token in ["xet tot nghiep", "tot nghiep", "trao bang", "ra truong"]):
            return StructuredFactType.GRADUATION
        if any(token in haystack for token in ["giay xac nhan", "giay gioi thieu", "thu tuc", "bao luu", "tam ngung", "thoi hoc"]):
            return StructuredFactType.PROCEDURE
        if any(token in haystack for token in ["ke hoach dao tao nam hoc", "ke hoach nam", "nghi he", "hoc ky he", "khai giang"]):
            return StructuredFactType.ANNUAL_PLAN
        if any(token in haystack for token in ["canh bao hoc vu", "canh bao hoc tap", "canh bao sinh vien", "xu ly hoc vu"]):
            return StructuredFactType.ACADEMIC_WARNING
        if any(token in haystack for token in ["dang ky hoc phan", "xac nhan dkhp", "dkhp"]):
            return StructuredFactType.REGISTRATION
        if any(token in haystack for token in ["chuong trinh dao tao", "ctdt", "ke hoach hoc tap"]):
            return StructuredFactType.CURRICULUM
        if any(token in haystack for token in ["hoc bong", "kkht", "khuyen khich hoc tap"]):
            return StructuredFactType.SCHOLARSHIP
        return StructuredFactType.DOCUMENT_SUMMARY

    def _compact(self, text: str, limit: int = 360) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."

    def _extract_segments(self, document: CollectedDocument, fact_type: StructuredFactType) -> list[str]:
        source_text = " ".join(filter(None, [document.summary or "", document.cleaned_content or ""]))
        normalized = self._normalize(source_text)
        segments = [segment.strip(" -*") for segment in re.split(r"(?<=[.!?])\s+|\n+", source_text) if segment.strip()]
        if not segments:
            return []

        relevant_tokens = {
            StructuredFactType.ANNUAL_PLAN: ["thang", "hoc ky", "khai giang", "tet", "/202", "06/202", "07/202", "08/202"],
            StructuredFactType.TUITION: ["dot", "hoc phi", "22/02", "17/05", "tra cuu", "cam thi", "xoa thong tin dang ky"],
            StructuredFactType.ENGLISH_REQUIREMENT: ["toeic", "ielts", "vstep", "vnu ept", "chuan dau ra"],
            StructuredFactType.GRADUATION: ["dang ky", "xet tot nghiep", "trao bang", "ho so"],
            StructuredFactType.PROCEDURE: ["thu tuc", "giay", "xac nhan", "gioi thieu", "bao luu", "tam ngung"],
            StructuredFactType.ACADEMIC_WARNING: ["canh bao", "ket qua hoc tap", "dkhp", "xu ly hoc vu"],
            StructuredFactType.REGISTRATION: ["dkhp", "dang ky hoc phan", "xac nhan dkhp"],
        }.get(fact_type, [])

        selected: list[str] = []
        for segment in segments:
            normalized_segment = self._normalize(segment)
            if relevant_tokens and not any(token in normalized_segment for token in relevant_tokens):
                continue
            if normalized_segment == normalized:
                continue
            selected.append(self._compact(segment, limit=280))
            if len(selected) >= 3:
                break
        return selected

    def _extract_value_json(self, document: CollectedDocument, metadata: dict) -> dict:
        haystack = self._normalize(" ".join(filter(None, [document.title, document.summary or "", document.cleaned_content or ""])))
        toeic_scores = sorted({match for match in re.findall(r"toeic[^0-9]{0,12}(\d{3})", haystack)})
        ielts_scores = sorted({match for match in re.findall(r"ielts[^0-9]{0,12}(\d(?:\.\d)?)", haystack)})
        return {
            "document_kind": metadata.get("document_kind"),
            "school_years": metadata.get("school_years", []),
            "applies_to_programs": metadata.get("applies_to_programs", []),
            "applies_to_cohorts": metadata.get("applies_to_cohorts", []),
            "freshness_bucket": metadata.get("freshness_bucket"),
            "toeic_scores": toeic_scores,
            "ielts_scores": ielts_scores,
        }

    def sync_document_facts(self, db: Session, document: CollectedDocument) -> list[StructuredKnowledgeFact]:
        db.query(StructuredKnowledgeFact).filter(StructuredKnowledgeFact.document_id == document.id).delete()
        metadata = self.metadata.build_metadata(
            title=document.title,
            text=document.cleaned_content or document.summary or "",
            tags=document.tags or [],
            published_at=document.published_at,
            updated_source_at=document.updated_source_at,
            url=document.url,
        )
        fact_type = self._infer_fact_type(document)
        confidence = ConfidenceLevel.HIGH if document.is_official_uit else ConfidenceLevel.MEDIUM
        school_year = metadata.get("school_years", [None])[0] if metadata.get("school_years") else None
        effective_from = None
        effective_to = None
        if metadata.get("effective_from"):
            effective_from = datetime.fromisoformat(str(metadata["effective_from"]))
        if metadata.get("effective_to"):
            effective_to = datetime.fromisoformat(str(metadata["effective_to"]))

        base_fact = StructuredKnowledgeFact(
            document_id=document.id,
            fact_type=fact_type,
            title=document.title,
            fact_text=self._compact(document.summary or document.cleaned_content or ""),
            school_year=school_year,
            effective_from=effective_from,
            effective_to=effective_to,
            applies_to_programs=metadata.get("applies_to_programs"),
            applies_to_cohorts=metadata.get("applies_to_cohorts"),
            value_json=self._extract_value_json(document, metadata),
            confidence_level=confidence,
        )
        db.add(base_fact)
        facts = [base_fact]

        for index, segment in enumerate(self._extract_segments(document, fact_type), start=1):
            fact = StructuredKnowledgeFact(
                document_id=document.id,
                fact_type=fact_type,
                title=f"{document.title} - ý chính {index}",
                fact_text=segment,
                school_year=school_year,
                effective_from=effective_from,
                effective_to=effective_to,
                applies_to_programs=metadata.get("applies_to_programs"),
                applies_to_cohorts=metadata.get("applies_to_cohorts"),
                value_json={**self._extract_value_json(document, metadata), "segment_index": index},
                confidence_level=confidence,
            )
            db.add(fact)
            facts.append(fact)

        db.flush()
        return facts

    def search_facts(
        self,
        db: Session,
        query: str,
        *,
        context_document_ids: list[int] | None = None,
        limit: int = 5,
    ) -> list[RankedStructuredFact]:
        topics = self._query_topics(query)
        normalized_query = self._normalize(query)
        query_years = set(re.findall(r"\b20\d{2}\b", normalized_query))
        tokens = [token for token in re.findall(r"[a-z0-9]+", normalized_query) if len(token) >= 3]
        ranked: list[RankedStructuredFact] = []

        for fact in db.query(StructuredKnowledgeFact).all():
            haystack = self._normalize(
                " ".join(
                    filter(
                        None,
                        [
                            fact.title,
                            fact.fact_text,
                            fact.school_year or "",
                            " ".join(fact.applies_to_programs or []),
                            " ".join(fact.applies_to_cohorts or []),
                            " ".join((fact.value_json or {}).get("school_years", [])),
                        ],
                    )
                )
            )
            token_hits = sum(1 for token in tokens if token in haystack)
            score = token_hits * 0.28

            if topics and self._fact_type_value(fact.fact_type) in topics:
                score += 1.4
            if context_document_ids and fact.document_id in context_document_ids:
                score += 0.8
            if fact.document and fact.document.is_official_uit:
                score += 0.1

            if query_years:
                fact_years = set(re.findall(r"\b20\d{2}\b", haystack))
                matched_years = query_years.intersection(fact_years)
                score += 0.22 * len(matched_years)

            if fact.school_year and fact.school_year.replace("-", " ") in normalized_query:
                score += 0.4
            if "freshness_bucket" in (fact.value_json or {}) and fact.value_json.get("freshness_bucket") == "CURRENT":
                score += 0.05

            if score <= 0:
                continue
            ranked.append(RankedStructuredFact(fact=fact, score=score))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]
