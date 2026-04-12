from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.data_paths import resolve_data_dir
from app.services.rag_evaluation_service import RagEvaluationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chạy bộ đánh giá retrieval + facts cho Studify RAG.")
    parser.add_argument("--top-k", type=int, default=5, help="Số context/fact top-K cho mỗi query.")
    parser.add_argument(
        "--benchmark-file",
        default=str(resolve_data_dir() / "evaluation" / "uit_rag_suite.json"),
        help="Đường dẫn file benchmark JSON.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    init_db()
    db = SessionLocal()
    try:
        result = await RagEvaluationService().evaluate(db, Path(args.benchmark_file), top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
