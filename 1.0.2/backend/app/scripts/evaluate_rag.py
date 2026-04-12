from __future__ import annotations

import argparse
import asyncio
import json
import unicodedata
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.data_paths import resolve_data_dir
from app.services.query_classifier import analyze_query
from app.services.rag_service import RagService


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", (value or "").lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def load_benchmarks(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Studify retrieval quality on a small UIT benchmark set.")
    parser.add_argument("--top-k", type=int, default=4, help="Number of retrieved contexts per query.")
    parser.add_argument(
        "--benchmark-file",
        default=str(resolve_data_dir() / "evaluation" / "uit_rag_queries.json"),
        help="Path to benchmark JSON file.",
    )
    return parser.parse_args()


async def evaluate(db: Session, benchmark_path: Path, top_k: int) -> dict:
    rag = RagService()
    benchmarks = load_benchmarks(benchmark_path)

    retrieval_hits = 0
    official_hits = 0
    classifier_hits = 0
    rows: list[dict] = []

    for item in benchmarks:
        query = str(item["query"])
        expected_keywords = [normalize_text(keyword) for keyword in item.get("expected_keywords", [])]
        expected_category = item.get("expected_category")
        require_official = bool(item.get("require_official", False))

        contexts = await rag.retrieve(db, query, limit=top_k)
        analysis = analyze_query(query)
        classifier_ok = expected_category is None or analysis.category == expected_category
        classifier_hits += int(classifier_ok)

        matched = False
        official_match = False
        for context in contexts:
            haystack = normalize_text(f"{context.document.title} {context.document.url} {context.excerpt}")
            if expected_keywords and any(keyword in haystack for keyword in expected_keywords):
                matched = True
                if context.document.is_official_uit:
                    official_match = True
                break

        retrieval_hits += int(matched)
        official_hits += int((not require_official and matched) or (require_official and official_match))
        rows.append(
            {
                "query": query,
                "expected_category": expected_category,
                "predicted_category": analysis.category,
                "retrieval_hit": matched,
                "official_hit": official_match if require_official else matched,
                "top_titles": [context.document.title for context in contexts],
            }
        )

    total = max(len(benchmarks), 1)
    return {
        "benchmark_file": str(benchmark_path),
        "total_queries": len(benchmarks),
        "top_k": top_k,
        "retrieval_hit_rate": round(retrieval_hits / total, 3),
        "official_hit_rate": round(official_hits / total, 3),
        "classifier_hit_rate": round(classifier_hits / total, 3),
        "rows": rows,
    }


async def main() -> None:
    args = parse_args()
    init_db()
    db = SessionLocal()
    try:
        result = await evaluate(db, Path(args.benchmark_file), args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
