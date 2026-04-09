from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.knowledge import CollectedDocument
from app.services.ollama_service import OllamaService
from app.services.qdrant_service import QdrantService


@dataclass
class RetrievedContext:
    document: CollectedDocument
    excerpt: str
    score: float


@dataclass
class CandidateContext:
    document: CollectedDocument
    excerpt: str
    vector_score: float = 0.0
    lexical_score: float = 0.0


class RagService:
    def __init__(self) -> None:
        self.ollama = OllamaService()
        self.qdrant = QdrantService()

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower())
        stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return re.sub(r"\s+", " ", stripped).strip()

    def _extract_tokens(self, query: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9]+", self._normalize(query))
        unique_tokens: list[str] = []
        seen_tokens: set[str] = set()
        for token in tokens:
            if len(token) < 3 or token in seen_tokens:
                continue
            seen_tokens.add(token)
            unique_tokens.append(token)
        return unique_tokens

    def _lexical_score(self, query: str, document: CollectedDocument, excerpt: str) -> float:
        normalized_query = self._normalize(query)
        tokens = self._extract_tokens(query)
        if not tokens:
            return 0.0

        title = self._normalize(document.title)
        body = self._normalize(" ".join(filter(None, [excerpt, document.summary or "", document.cleaned_content or ""])))
        title_hits = sum(1 for token in tokens if token in title)
        body_hits = sum(1 for token in tokens if token in body)
        title_ratio = min(1.0, title_hits / max(1, min(len(tokens), 4)))
        body_ratio = min(1.0, body_hits / max(1, len(tokens)))
        phrase_bonus = 0.15 if normalized_query and normalized_query in f"{title} {body}" else 0.0
        coverage_bonus = 0.2 if title_hits >= max(2, len(tokens) // 2) else 0.0
        official_bonus = 0.05 if document.is_official_uit else 0.0
        return (title_ratio * 0.7) + (body_ratio * 0.15) + phrase_bonus + coverage_bonus + official_bonus

    def _candidate_excerpt(self, document: CollectedDocument, excerpt: str | None = None) -> str:
        source_text = excerpt or document.summary or document.cleaned_content or ""
        return source_text[:500]

    async def retrieve(self, db: Session, query: str, limit: int = 4) -> list[RetrievedContext]:
        candidates: dict[int, CandidateContext] = {}
        vector: list[float] = []

        try:
            embedding = await self.ollama.create_embedding(query)
            if isinstance(embedding, list):
                vector = embedding
        except Exception:
            vector = []

        scored_points = self.qdrant.search(vector, limit=max(limit * 3, limit)) if vector else []
        for item in scored_points:
            payload = item.payload or {}
            document_id = payload.get("document_id")
            if not document_id:
                continue
            document = db.query(CollectedDocument).filter(CollectedDocument.id == document_id).first()
            if not document:
                continue
            excerpt = self._candidate_excerpt(document, payload.get("content"))
            candidate = candidates.get(document_id)
            if candidate is None:
                candidate = CandidateContext(document=document, excerpt=excerpt)
                candidates[document_id] = candidate
            candidate.vector_score = max(candidate.vector_score, float(item.score or 0))
            if len(excerpt) > len(candidate.excerpt):
                candidate.excerpt = excerpt

        for document in (
            db.query(CollectedDocument)
            .order_by(CollectedDocument.updated_source_at.desc().nullslast(), CollectedDocument.id.desc())
            .limit(400)
            .all()
        ):
            candidate = candidates.get(document.id)
            if candidate is None:
                candidate = CandidateContext(document=document, excerpt=self._candidate_excerpt(document))
                candidates[document.id] = candidate

        ranked_contexts: list[RetrievedContext] = []
        for candidate in candidates.values():
            candidate.lexical_score = self._lexical_score(query, candidate.document, candidate.excerpt)
            final_score = (candidate.vector_score * 0.35) + (candidate.lexical_score * 0.65)
            if candidate.vector_score == 0 and candidate.lexical_score == 0:
                continue
            ranked_contexts.append(
                RetrievedContext(
                    document=candidate.document,
                    excerpt=candidate.excerpt,
                    score=final_score,
                )
            )

        ranked_contexts.sort(key=lambda item: item.score, reverse=True)
        return ranked_contexts[:limit]
