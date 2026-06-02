from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.data_paths import resolve_data_dir
from app.services.text_utils import clean_text

BLOCKED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".zip",
    ".rar",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}

BLOCKED_KEYWORDS = [
    "tuyen-sinh",
    "admission",
    "calendar",
    "mailto:",
    "tel:",
    "facebook.com",
    "youtube.com",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:120] or "document"


def iter_candidate_links(base_url: str, domain: str, html: str, priority_keywords: Iterable[str]) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates: dict[str, int] = {}
    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        if not parsed.scheme.startswith("http"):
            continue
        if not parsed.netloc.endswith(domain):
            continue
        if any(keyword in absolute_url.lower() for keyword in BLOCKED_KEYWORDS):
            continue
        if any(parsed.path.lower().endswith(extension) for extension in BLOCKED_EXTENSIONS):
            continue
        score = 0
        normalized = absolute_url.lower()
        for keyword in priority_keywords:
            if keyword.lower() in normalized:
                score += 5
        if "thong-bao" in normalized or "notice" in normalized:
            score += 3
        if "sinh-vien" in normalized or "student" in normalized:
            score += 2
        candidates[absolute_url] = max(score, candidates.get(absolute_url, 0))
    return [item[0] for item in sorted(candidates.items(), key=lambda pair: (-pair[1], pair[0]))]


def extract_title_and_text(url: str, html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = (
        (soup.find("meta", attrs={"property": "og:title"}) or {}).get("content")
        or (soup.title.string.strip() if soup.title and soup.title.string else "")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
        or urlparse(url).path.strip("/").split("/")[-1]
        or "Tài liệu UIT"
    )
    text = clean_text(soup.get_text(" ", strip=True))
    return title.strip(), text


async def fetch_text(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    response = await client.get(url)
    response.raise_for_status()
    return extract_title_and_text(url, response.text)


def load_registry(limit_override: int | None = None) -> list[dict]:
    data_dir = resolve_data_dir()
    registry_path = data_dir / "source_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if limit_override is None:
        return registry

    patched_registry = []
    for source in registry:
        patched_source = dict(source)
        patched_source["max_pages"] = limit_override
        patched_registry.append(patched_source)
    return patched_registry


async def crawl(limit_override: int | None = None) -> None:
    data_dir = resolve_data_dir()
    snapshots_dir = data_dir / "snapshots"
    processed_dir = data_dir / "processed"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    registry = load_registry(limit_override=limit_override)
    manifest_records: list[dict] = []
    processed_records: list[dict] = []

    async with httpx.AsyncClient(
        timeout=25,
        headers={"User-Agent": "StudifyBot/1.0 (+https://uit.edu.vn)"},
        follow_redirects=True,
    ) as client:
        for source in registry:
            source_dir = snapshots_dir / source["id"]
            source_dir.mkdir(parents=True, exist_ok=True)

            print(f"[crawl] {source['name']} -> {source['base_url']}")
            try:
                response = await client.get(source["base_url"])
                response.raise_for_status()
                home_html = response.text
            except Exception as exc:
                print(f"[skip] {source['name']}: {exc}")
                continue

            candidate_links = iter_candidate_links(
                source["base_url"],
                source["domain"],
                home_html,
                source.get("priority_keywords", []),
            )
            urls = [source["base_url"], *candidate_links[: source.get("max_pages", 4)]]
            urls = list(dict.fromkeys(urls))

            for index, url in enumerate(urls, start=1):
                try:
                    title, text = await fetch_text(client, url)
                except Exception as exc:
                    print(f"[error] {url}: {exc}")
                    continue

                if len(text) < 160:
                    continue

                file_name = f"{index:02d}-{slugify(title)}.md"
                snapshot_path = source_dir / file_name
                snapshot_body = "\n".join(
                    [
                        f"# {title}",
                        "",
                        f"- URL: {url}",
                        f"- Nguồn: {source['name']}",
                        f"- Thời điểm crawl: {datetime.now(timezone.utc).isoformat()}",
                        "",
                        "## Nội dung trích xuất",
                        "",
                        text,
                        "",
                    ]
                )
                snapshot_path.write_text(snapshot_body, encoding="utf-8")

                record = {
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "domain": source["domain"],
                    "is_official_uit": bool(source["official"]),
                    "title": title,
                    "url": url,
                    "snapshot_file": str(snapshot_path.relative_to(data_dir)),
                    "text": text,
                    "summary": text[:400],
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "tags": source.get("priority_keywords", []),
                }
                manifest_records.append(record)
                processed_records.append(record)

            manifest_path = source_dir / "manifest.json"
            source_manifest = [item for item in manifest_records if item["source_id"] == source["id"]]
            manifest_path.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    jsonl_path = processed_dir / "uit_documents.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as file_pointer:
        for record in processed_records:
            file_pointer.write(json.dumps(record, ensure_ascii=False) + "\n")

    index_path = processed_dir / "manifest.json"
    index_path.write_text(json.dumps(processed_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] saved {len(processed_records)} documents into {data_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl public UIT content into Studify/backend/data")
    parser.add_argument("--limit-per-source", type=int, default=None, help="Override max_pages from source registry")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    await crawl(limit_override=args.limit_per_source)


if __name__ == "__main__":
    asyncio.run(main())
