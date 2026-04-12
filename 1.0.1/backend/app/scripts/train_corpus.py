from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urldefrag, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.services.data_paths import resolve_data_dir
from app.services.text_utils import clean_text, content_hash

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
    "mailto:",
    "tel:",
    "facebook.com",
    "youtube.com",
    "/en/",
    "lang=en",
]

GLOBAL_PRIORITY_KEYWORDS = [
    "sinh-vien",
    "student",
    "hoc-vu",
    "dao-tao",
    "thong-bao",
    "huong-dan",
    "quy-che",
    "quy-dinh",
    "tot-nghiep",
    "hoc-phi",
    "hoc-bong",
    "giay",
    "lich-thi",
    "lich-hoc",
    "chuong-trinh",
]

SOURCE_SEED_PATHS: dict[str, list[str]] = {
    "uit-main": [
        "/",
        "/dao-tao",
        "/sinh-vien",
        "/thong-bao",
        "/tin-tuc-su-kien",
    ],
    "uit-daa": [
        "/sinhvien",
        "/thongbao",
        "/huong-dan",
        "/bieu-mau",
        "/quy-trinh",
    ],
    "uit-student": [
        "/",
        "/thongbao",
        "/quydinhdaotao",
        "/quydinh",
        "/quy-che-quy-dinh-dao-tao-dai-hoc-cua-dhqg-hcm",
        "/moc-thoi-gian",
        "/hoc-bong",
    ],
    "uit-ctsv": [
        "/",
        "/quy-che-quy-dinh",
        "/hoc-bong",
        "/tin-tuc",
        "/ho-tro-sinh-vien",
    ],
    "uit-courses": [
        "/",
        "/login/index.php",
    ],
    "uit-oep": [
        "/vi",
        "/vi/tong-quan",
        "/vi/gallery-category/hoc-tap",
        "/vi/chuong-trinh-tien-tien",
        "/vi/tong-quan-ve-chuong-trinh-chat-luong-cao",
        "/vi/tong-quan-ve-chuong-trinh-lien-ket-uon",
        "/vi/tong-quan-ve-chuong-trinh-lien-ket-bcu",
        "/vi/cu-nhan-tai-nang-thiet-ke-vi-mach",
    ],
}

SOURCE_DIRECT_URLS: dict[str, list[str]] = {
    "uit-student": [
        "https://student.uit.edu.vn/sites/default/files/files/QD%20ban%20hanh%20quy%20che%20dao%20tao%282%29.pdf",
        "https://student.uit.edu.vn/sites/default/files/files/Quy%20che%20Dao%20tao%20theo%20tin%20chi_UIT.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/1195-qd-dhqg_27-9-2019_quy_dinh_dao_tao_song_nganh_dhqg.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/1342-qd-dhqg_30-9-2022_quy_che_dao_tao.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/540_qd_dhqg_9-5-2023_quy_dinh_mo_nganh.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/170_qd_dhqg_27_02_2018_cong_nhan_chung_chi_ngoai_ngu.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/707_qd_dhqg23_6_2022_quy_che_tuyen_sinh_trinh_do_dh.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/836_qd_dhqg_19_7_2021_quy_che_tuyen_sinh_trinh_do_dai_hoc_dhqghcm.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/1658-qd-dhqg_24-12-2020_phe_duyet_thi_diem_bo_pcnl_svtn_dhqghcm.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/bb1528_dhqg_2-8-2022_hop_ve_cong_tac_dao_tao.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202310/cv671-dhqg_18-4-2022_su_dung_chung_chi_vnu-ept.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202412/507-qd-dhcntt-27-5-2024_quy_che_dao_tao_cho_sinh_vien.pdf",
        "https://student.uit.edu.vn/sites/daa/files/202505/1314-qd-bgddt_13-05-2025_ban_hanh_chuan_ctdt_ve_vi_mach_ban_dan_trinh_do_dh_ths.pdf",
    ],
    "uit-ctsv": [
        "https://ctsv.uit.edu.vn/sites/default/files/201607/33_qd_dhcntt_ctsv5_7_2016_scan.pdf",
        "https://ctsv.uit.edu.vn/sites/default/files/202204/47_tb_dhcntt19_4_2022_scan.pdf",
    ],
    "uit-oep": [
        "https://oep.uit.edu.vn/sites/oep/files/uploads/files/202007/thong_bao_dkhp-hk1_2020-2021.pdf",
        "https://oep.uit.edu.vn/sites/oep/files/uploads/files/202112/thong_bao_dkhp-hk2_2021-2022.pdf",
    ],
}

SKIP_STORE_PATHS = {
    "",
    "/",
    "/thong-bao",
    "/thongbao",
    "/tin-tuc-su-kien",
    "/sinhvien",
    "/ho-tro-sinh-vien",
    "/quy-che-quy-dinh",
}

TRAINING_DISABLED_SOURCE_IDS = {"uit-courses"}


@dataclass(slots=True)
class UrlCandidate:
    url: str
    score: int
    kind: str


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:120] or "document"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str) -> str:
    clean_url = urldefrag(url.strip())[0]
    parsed = urlparse(clean_url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in {"page", "amp", "replytocom", "fbclid", "gclid", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
    ]
    normalized = urlunparse(parsed._replace(query=urlencode(filtered_query, doseq=True)))
    return normalized.rstrip("/") or normalized


def is_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.path.lower().endswith(".pdf") or ".pdf?" in url.lower()


def host_matches_domain(netloc: str, domain: str) -> bool:
    normalized_host = netloc.lower()
    normalized_domain = domain.lower()
    return normalized_host in {normalized_domain, f"www.{normalized_domain}"} or (
        normalized_domain.startswith("www.") and normalized_host == normalized_domain.removeprefix("www.")
    )


def is_allowed_url(url: str, domain: str) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return False
    if not host_matches_domain(parsed.netloc, domain):
        return False
    normalized = url.lower()
    if any(keyword in normalized for keyword in BLOCKED_KEYWORDS):
        return False
    if any(parsed.path.lower().endswith(extension) for extension in BLOCKED_EXTENSIONS):
        return False
    return True


def score_candidate(url: str, anchor_text: str, priority_keywords: list[str]) -> int:
    normalized_url = url.lower()
    normalized_anchor = anchor_text.lower()
    score = 1

    if is_pdf_url(url):
        score += 10

    for keyword in [*GLOBAL_PRIORITY_KEYWORDS, *priority_keywords]:
        if keyword.lower() in normalized_url:
            score += 6
        if keyword.lower() in normalized_anchor:
            score += 4

    if any(marker in normalized_url for marker in ["quy-che", "quy-dinh", "huong-dan", "thong-bao"]):
        score += 5

    if any(marker in normalized_anchor for marker in ["quy chế", "quy định", "hướng dẫn", "thông báo", "học phí", "học bổng"]):
        score += 5

    path_depth = len([segment for segment in urlparse(url).path.split("/") if segment])
    if 2 <= path_depth <= 6:
        score += 2

    return score


def extract_candidate_links(base_url: str, domain: str, html: str, priority_keywords: list[str]) -> list[UrlCandidate]:
    soup = BeautifulSoup(html, "lxml")
    discovered: dict[str, UrlCandidate] = {}
    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue

        absolute_url = normalize_url(urljoin(base_url, href))
        if not is_allowed_url(absolute_url, domain):
            continue

        anchor_text = clean_text(anchor.get_text(" ", strip=True))
        score = score_candidate(absolute_url, anchor_text, priority_keywords)
        kind = "pdf" if is_pdf_url(absolute_url) else "html"
        existing = discovered.get(absolute_url)
        if existing is None or score > existing.score:
            discovered[absolute_url] = UrlCandidate(url=absolute_url, score=score, kind=kind)

    return sorted(discovered.values(), key=lambda item: (-item.score, item.url))


def extract_title_and_text(url: str, html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = (
        (soup.find("meta", attrs={"property": "og:title"}) or {}).get("content")
        or (soup.find("meta", attrs={"name": "title"}) or {}).get("content")
        or (soup.title.string.strip() if soup.title and soup.title.string else "")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
        or urlparse(url).path.strip("/").split("/")[-1]
        or "UIT document"
    )

    main_selectors = [
        "article",
        "main",
        ".node",
        ".content",
        ".entry-content",
        ".post-content",
        "#content",
    ]

    text_candidates: list[str] = []
    for selector in main_selectors:
        for node in soup.select(selector):
            text = clean_text(node.get_text(" ", strip=True))
            if len(text) > 240:
                text_candidates.append(text)

    body_text = clean_text(soup.get_text(" ", strip=True))
    text = max(text_candidates or [body_text], key=len)
    return title.strip(), text


def extract_pdf_text_with_pdftotext(pdf_path: Path) -> str:
    if shutil.which("pdftotext") is None:
        return ""

    command = ["pdftotext", "-layout", str(pdf_path), "-"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return clean_text(result.stdout)


def extract_pdf_text_with_pypdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return ""

    pages: list[str] = []
    for page in reader.pages[:40]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return clean_text(" ".join(pages))


def extract_pdf_text_with_ocr(pdf_path: Path, work_dir: Path, max_pages: int = 8) -> tuple[str, bool]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return "", False

    if shutil.which("pdftoppm") is None:
        return "", False

    image_dir = work_dir / f"{pdf_path.stem}-ocr"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_prefix = image_dir / "page"
    command = [
        "pdftoppm",
        "-png",
        "-f",
        "1",
        "-l",
        str(max_pages),
        str(pdf_path),
        str(image_prefix),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return "", False

    engine = RapidOCR()
    extracted_pages: list[str] = []
    for image_path in sorted(image_dir.glob("*.png")):
        try:
            output, _ = engine(str(image_path))
        except Exception:
            continue
        if not output:
            continue
        page_text = " ".join(item[1] for item in output if len(item) > 1 and item[1])
        if page_text:
            extracted_pages.append(page_text)

    return clean_text(" ".join(extracted_pages)), bool(extracted_pages)


def extract_pdf_text(pdf_path: Path, work_dir: Path) -> tuple[str, bool]:
    text = extract_pdf_text_with_pdftotext(pdf_path)
    if len(text) >= 240:
        return text, False

    fallback_text = extract_pdf_text_with_pypdf(pdf_path)
    if len(fallback_text) > len(text):
        text = fallback_text
    if len(text) >= 240:
        return text, False

    ocr_text, used_ocr = extract_pdf_text_with_ocr(pdf_path, work_dir)
    if len(ocr_text) > len(text):
        text = ocr_text
    return text, used_ocr


async def fetch_sitemap_urls(client: httpx.AsyncClient, source: dict) -> list[UrlCandidate]:
    sitemap_urls: list[str] = []
    robots_url = urljoin(source["base_url"], "/robots.txt")
    try:
        response = await client.get(robots_url)
        if response.status_code == 200:
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_urls.append(line.split(":", 1)[1].strip())
    except Exception:
        pass

    for fallback in ["/sitemap.xml", "/sitemap_index.xml"]:
        sitemap_urls.append(urljoin(source["base_url"], fallback))

    unique_sitemaps = list(dict.fromkeys(sitemap_urls))
    discovered: dict[str, UrlCandidate] = {}

    for sitemap_url in unique_sitemaps[:4]:
        try:
            response = await client.get(sitemap_url)
            if response.status_code != 200:
                continue
        except Exception:
            continue

        locs = re.findall(r"<loc>(.*?)</loc>", response.text, flags=re.IGNORECASE)
        for loc in locs[:400]:
            normalized_url = normalize_url(loc)
            if not is_allowed_url(normalized_url, source["domain"]):
                continue
            score = score_candidate(normalized_url, "", source.get("priority_keywords", []))
            kind = "pdf" if is_pdf_url(normalized_url) else "html"
            existing = discovered.get(normalized_url)
            if existing is None or score > existing.score:
                discovered[normalized_url] = UrlCandidate(url=normalized_url, score=score + 3, kind=kind)

    return sorted(discovered.values(), key=lambda item: (-item.score, item.url))


def build_seed_candidates(source: dict) -> list[UrlCandidate]:
    candidates: list[UrlCandidate] = []
    for path in SOURCE_SEED_PATHS.get(source["id"], []):
        absolute_url = normalize_url(urljoin(source["base_url"], path))
        if not is_allowed_url(absolute_url, source["domain"]):
            continue
        candidates.append(
            UrlCandidate(
                url=absolute_url,
                score=score_candidate(absolute_url, "", source.get("priority_keywords", [])) + 20,
                kind="pdf" if is_pdf_url(absolute_url) else "html",
            )
        )
    for absolute_url in SOURCE_DIRECT_URLS.get(source["id"], []):
        normalized_url = normalize_url(absolute_url)
        if not is_allowed_url(normalized_url, source["domain"]):
            continue
        candidates.append(
            UrlCandidate(
                url=normalized_url,
                score=score_candidate(normalized_url, "", source.get("priority_keywords", [])) + 40,
                kind="pdf" if is_pdf_url(normalized_url) else "html",
            )
        )
    if not candidates:
        candidates.append(UrlCandidate(url=normalize_url(source["base_url"]), score=20, kind="html"))
    return candidates


def should_store_document(url: str, title: str, file_type: str) -> bool:
    if file_type == "pdf":
        return True

    parsed = urlparse(url)
    normalized_path = parsed.path.rstrip("/")
    if normalized_path in SKIP_STORE_PATHS:
        return False

    normalized_url = url.lower()
    normalized_title = title.lower()
    if "tuyen-dung" in normalized_url:
        return False
    if normalized_title in {
        "trường đại học công nghệ thông tin - đại học quốc gia thành phố hồ chí minh",
        "trường đại học công nghệ thông tin - đại học quốc gia thành phố hồ chí minh | cổng thông tin đào tạo",
    }:
        return False
    return True


def load_registry(allowed_domains: set[str] | None = None) -> list[dict]:
    data_dir = resolve_data_dir()
    registry_path = data_dir / "source_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    filtered_registry = [source for source in registry if source.get("id") not in TRAINING_DISABLED_SOURCE_IDS]
    if allowed_domains is None:
        return filtered_registry
    return [source for source in filtered_registry if source.get("domain") in allowed_domains]


def make_snapshot_markdown(title: str, source_name: str, url: str, crawled_at: str, text: str, file_type: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- URL: {url}",
            f"- Source: {source_name}",
            f"- Crawled at: {crawled_at}",
            f"- File type: {file_type}",
            "",
            "## Extracted content",
            "",
            text,
            "",
        ]
    )


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file_pointer:
        for record in records:
            file_pointer.write(json.dumps(record, ensure_ascii=False) + "\n")


async def collect_training_corpus(
    target_documents: int = 30,
    min_text_length: int = 240,
    allowed_domains: set[str] | None = None,
) -> dict:
    data_dir = resolve_data_dir()
    snapshots_dir = data_dir / "snapshots"
    processed_dir = data_dir / "processed"
    pdf_dir = data_dir / "pdfs"
    ocr_dir = data_dir / "ocr"
    for directory in [snapshots_dir, processed_dir, pdf_dir, ocr_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    registry = load_registry(allowed_domains=allowed_domains)
    records: list[dict] = []
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    total_target = max(target_documents, 1)
    total_sources = max(len(registry), 1)
    per_source_target = max(4, total_target // max(total_sources - 1, 1))

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(25.0, connect=10.0),
        headers={"User-Agent": "StudifyTrainer/1.0 (+https://uit.edu.vn)"},
        follow_redirects=True,
    ) as client:
        for source in registry:
            if len(records) >= total_target:
                break

            source_records: list[dict] = []
            source_snapshot_dir = snapshots_dir / source["id"]
            source_pdf_dir = pdf_dir / source["id"]
            source_snapshot_dir.mkdir(parents=True, exist_ok=True)
            source_pdf_dir.mkdir(parents=True, exist_ok=True)

            queue: dict[str, UrlCandidate] = {}
            visited_urls: set[str] = set()
            for candidate in build_seed_candidates(source):
                queue[candidate.url] = candidate

            for candidate in (await fetch_sitemap_urls(client, source))[:40]:
                existing = queue.get(candidate.url)
                if existing is None or candidate.score > existing.score:
                    queue[candidate.url] = candidate

            print(f"[train] source={source['id']} queued={len(queue)}")

            while queue and len(source_records) < per_source_target and len(records) < total_target:
                candidate = sorted(queue.values(), key=lambda item: (-item.score, item.url))[0]
                queue.pop(candidate.url, None)

                if candidate.url in visited_urls or candidate.url in seen_urls:
                    continue
                visited_urls.add(candidate.url)

                try:
                    response = await client.get(candidate.url)
                    response.raise_for_status()
                except Exception as exc:
                    print(f"[skip] {candidate.url} -> {exc}")
                    continue

                if candidate.kind == "pdf" or "application/pdf" in response.headers.get("content-type", "").lower():
                    title = Path(urlparse(candidate.url).path).name or "uit-pdf"
                    file_name = f"{len(source_records) + 1:02d}-{slugify(title)}.pdf"
                    pdf_path = source_pdf_dir / file_name
                    pdf_path.write_bytes(response.content)
                    pdf_text, used_ocr = extract_pdf_text(pdf_path, ocr_dir)
                    if len(pdf_text) < min_text_length:
                        print(f"[skip-pdf] short text {candidate.url}")
                        continue

                    hash_value = content_hash(pdf_text)
                    if hash_value in seen_hashes:
                        continue

                    seen_hashes.add(hash_value)
                    seen_urls.add(candidate.url)
                    crawled_at = now_iso()
                    snapshot_name = f"{len(source_records) + 1:02d}-{slugify(title)}.md"
                    snapshot_path = source_snapshot_dir / snapshot_name
                    snapshot_path.write_text(
                        make_snapshot_markdown(title, source["name"], candidate.url, crawled_at, pdf_text, "pdf"),
                        encoding="utf-8",
                    )

                    record = {
                        "source_id": source["id"],
                        "source_name": source["name"],
                        "base_url": source["base_url"],
                        "domain": source["domain"],
                        "is_official_uit": bool(source["official"]),
                        "title": title,
                        "url": candidate.url,
                        "snapshot_file": str(snapshot_path.relative_to(data_dir)),
                        "download_file": str(pdf_path.relative_to(data_dir)),
                        "text": pdf_text,
                        "summary": pdf_text[:500],
                        "crawled_at": crawled_at,
                        "tags": source.get("priority_keywords", []),
                        "file_type": "pdf",
                        "ocr_used": used_ocr,
                    }
                    source_records.append(record)
                    records.append(record)
                    print(f"[pdf] {candidate.url}")
                    continue

                html = response.text
                page_title, page_text = extract_title_and_text(candidate.url, html)
                if len(page_text) >= min_text_length and should_store_document(candidate.url, page_title, "html"):
                    hash_value = content_hash(page_text)
                    if hash_value not in seen_hashes:
                        seen_hashes.add(hash_value)
                        seen_urls.add(candidate.url)
                        crawled_at = now_iso()
                        snapshot_name = f"{len(source_records) + 1:02d}-{slugify(page_title)}.md"
                        snapshot_path = source_snapshot_dir / snapshot_name
                        snapshot_path.write_text(
                            make_snapshot_markdown(page_title, source["name"], candidate.url, crawled_at, page_text, "html"),
                            encoding="utf-8",
                        )
                        record = {
                            "source_id": source["id"],
                            "source_name": source["name"],
                            "base_url": source["base_url"],
                            "domain": source["domain"],
                            "is_official_uit": bool(source["official"]),
                            "title": page_title,
                            "url": candidate.url,
                            "snapshot_file": str(snapshot_path.relative_to(data_dir)),
                            "text": page_text,
                            "summary": page_text[:500],
                            "crawled_at": crawled_at,
                            "tags": source.get("priority_keywords", []),
                            "file_type": "html",
                            "ocr_used": False,
                        }
                        source_records.append(record)
                        records.append(record)
                        print(f"[html] {candidate.url}")

                for discovered in extract_candidate_links(candidate.url, source["domain"], html, source.get("priority_keywords", []))[:50]:
                    if discovered.url in visited_urls or discovered.url in seen_urls:
                        continue
                    existing = queue.get(discovered.url)
                    if existing is None or discovered.score > existing.score:
                        queue[discovered.url] = discovered

            manifest_path = source_snapshot_dir / "manifest.json"
            manifest_path.write_text(json.dumps(source_records, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = processed_dir / "manifest.json"
    jsonl_path = processed_dir / "uit_documents.jsonl"
    manifest_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(jsonl_path, records)

    summary = {
        "target_documents": total_target,
        "collected_documents": len(records),
        "processed_jsonl": str(jsonl_path),
        "manifest": str(manifest_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the Studify RAG corpus before Docker startup.")
    parser.add_argument("--target-documents", type=int, default=30, help="Target number of documents to collect.")
    parser.add_argument("--min-text-length", type=int, default=240, help="Minimum cleaned text length for a kept document.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    await collect_training_corpus(
        target_documents=args.target_documents,
        min_text_length=args.min_text_length,
    )


if __name__ == "__main__":
    asyncio.run(main())
