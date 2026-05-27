from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.services.query_classifier import analyze_query
from app.services.rag_service import RagService, RetrievedContext
from app.services.structured_facts_service import StructuredFactsService


@dataclass(slots=True)
class EvaluationCase:
    query: str
    expected_category: str | None = None
    require_official: bool = False
    expected_keywords: list[str] | None = None
    expected_domains: list[str] | None = None
    expected_fact_types: list[str] | None = None
    expected_school_years: list[str] | None = None


class RagEvaluationService:
    def __init__(self) -> None:
        self.rag = RagService()
        self.facts = StructuredFactsService()

    def normalize_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFD", (value or "").lower().replace("đ", "d"))
        return "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    def load_cases(self, path: Path) -> list[EvaluationCase]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [EvaluationCase(**item) for item in payload]

    def _domain(self, url: str) -> str:
        return urlparse(url or "").netloc.lower().removeprefix("www.")

    def _fact_type_value(self, value: str | object) -> str:
        return value.value if hasattr(value, "value") else str(value)

    def _is_retrieval_hit(self, contexts: list[RetrievedContext], expected_keywords: list[str]) -> tuple[bool, float]:
        normalized_keywords = [self.normalize_text(keyword) for keyword in expected_keywords]
        first_rank = 0
        for index, context in enumerate(contexts, start=1):
            haystack = self.normalize_text(f"{context.document.title} {context.document.url} {context.excerpt}")
            if any(keyword in haystack for keyword in normalized_keywords):
                first_rank = index
                break
        if first_rank == 0:
            return False, 0.0
        return True, round(1 / first_rank, 3)

    async def evaluate_case(self, db: Session, case: EvaluationCase, top_k: int = 5) -> dict:
        contexts = await self.rag.retrieve(db, case.query, limit=top_k)
        fact_matches = self.facts.search_facts(
            db,
            case.query,
            context_document_ids=[item.document.id for item in contexts],
            limit=top_k,
        )
        analysis = analyze_query(case.query)

        retrieval_hit, reciprocal_rank = self._is_retrieval_hit(contexts, case.expected_keywords or [])
        classifier_hit = case.expected_category is None or analysis.category == case.expected_category

        if case.require_official:
            official_hit = any(
                context.document.is_official_uit
                and any(
                    self.normalize_text(keyword)
                    in self.normalize_text(f"{context.document.title} {context.document.url} {context.excerpt}")
                    for keyword in (case.expected_keywords or [])
                )
                for context in contexts
            )
        else:
            official_hit = retrieval_hit

        expected_domains = {domain.lower() for domain in (case.expected_domains or [])}
        domain_hit = (
            True
            if not expected_domains
            else any(self._domain(context.document.url) in expected_domains for context in contexts)
        )

        expected_fact_types = {item.upper() for item in (case.expected_fact_types or [])}
        expected_school_years = set(case.expected_school_years or [])
        fact_hit = True
        if expected_fact_types or expected_school_years:
            fact_hit = any(
                (
                    not expected_fact_types
                    or self._fact_type_value(item.fact.fact_type) in expected_fact_types
                )
                and (
                    not expected_school_years
                    or item.fact.school_year in expected_school_years
                    or bool(expected_school_years.intersection(set((item.fact.value_json or {}).get("school_years", []))))
                )
                for item in fact_matches
            )

        return {
            "query": case.query,
            "expected_category": case.expected_category,
            "predicted_category": analysis.category,
            "classifier_hit": classifier_hit,
            "retrieval_hit": retrieval_hit,
            "official_hit": official_hit,
            "domain_hit": domain_hit,
            "fact_hit": fact_hit,
            "reciprocal_rank": reciprocal_rank,
            "top_titles": [context.document.title for context in contexts],
            "top_domains": [self._domain(context.document.url) for context in contexts],
            "top_fact_types": [self._fact_type_value(item.fact.fact_type) for item in fact_matches],
            "top_fact_titles": [item.fact.title for item in fact_matches],
        }

    async def evaluate(self, db: Session, cases_path: Path, top_k: int = 5) -> dict:
        cases = self.load_cases(cases_path)
        rows = [await self.evaluate_case(db, case, top_k=top_k) for case in cases]
        total = max(len(rows), 1)
        return {
            "cases_path": str(cases_path),
            "total_queries": len(rows),
            "top_k": top_k,
            "metrics": {
                "classifier_hit_rate": round(sum(1 for row in rows if row["classifier_hit"]) / total, 3),
                "retrieval_hit_rate": round(sum(1 for row in rows if row["retrieval_hit"]) / total, 3),
                "official_hit_rate": round(sum(1 for row in rows if row["official_hit"]) / total, 3),
                "domain_hit_rate": round(sum(1 for row in rows if row["domain_hit"]) / total, 3),
                "fact_hit_rate": round(sum(1 for row in rows if row["fact_hit"]) / total, 3),
                "mrr": round(sum(row["reciprocal_rank"] for row in rows) / total, 3),
            },
            "failed_cases": [
                row
                for row in rows
                if not all([row["classifier_hit"], row["retrieval_hit"], row["official_hit"], row["domain_hit"], row["fact_hit"]])
            ],
            "rows": rows,
        }
