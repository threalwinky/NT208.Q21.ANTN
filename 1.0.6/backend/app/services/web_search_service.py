"""
Web search service - dùng Selenium + headless Chromium.

Tìm kiếm Google qua trình duyệt thật để tránh phụ thuộc API search bên thứ ba.
Nếu Google yêu cầu CAPTCHA trong container, service fallback sang DuckDuckGo HTML
để chatbot vẫn có dữ liệu web thay vì trả sai là không tìm thấy.
Sau khi có danh sách kết quả, fetch nhiều trang nguồn song song bằng async HTTP để tăng tốc.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

_CHROMIUM_BIN = os.environ.get("CHROMIUM_BIN", "/usr/bin/chromium")
_CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_BIN", "/usr/bin/chromedriver")

_GOOGLE_SEARCH_URL = "https://www.google.com/search"
_DUCKDUCKGO_SEARCH_URL = "https://html.duckduckgo.com/html/"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_GOOGLE_BLOCK_MARKERS = (
    "our systems have detected unusual traffic",
    "detected unusual traffic",
    "lưu lượng truy cập bất thường",
    "luu luong truy cap bat thuong",
    "google sorry",
)
_UIT_PRIORITY_DOMAINS = ("daa.uit.edu.vn", "oep.uit.edu.vn", "ctsv.uit.edu.vn")
_UIT_BROAD_DOMAINS = (
    "uit.edu.vn",
    "www.uit.edu.vn",
    "nc.uit.edu.vn",
    "inseclab.uit.edu.vn",
    "student.uit.edu.vn",
    "courses.uit.edu.vn",
    "khtc.uit.edu.vn",
)
_UIT_GENERAL_DOMAINS = (*_UIT_PRIORITY_DOMAINS, *_UIT_BROAD_DOMAINS)
_OTHER_SCHOOL_MARKERS = (
    "bach khoa",
    "hcmut",
    "hcmus",
    "khoa hoc tu nhien",
    "kinh te luat",
    "uel",
    "nhan van",
    "ussh",
    "hutech",
    "ton duc thang",
    "tdtu",
    "ueh",
    "fpt",
    "rmit",
    "hust",
    "neu",
    "ptit",
    "uet",
)
_UIT_QUERY_MARKERS = (
    "uit",
    "dai hoc cong nghe thong tin",
    "truong minh",
    "truong uit",
    "student uit",
    "daa",
    "oep",
    "ctsv",
    "hoc vu",
    "hoc bong",
    "giai thuong",
    "sinh vien",
    "giang vien",
    "doi ngu giang vien",
    "ctdt",
    "chuong trinh dao tao",
    "chuong trinh hoc",
    "mon chuyen nganh",
    "an toan thong tin",
    "hoc phan",
    "dkhp",
    "dang ky hoc phan",
    "lich thi",
    "lich hoc",
    "hoc phi",
    "canh bao hoc vu",
    "tot nghiep",
    "xet tot nghiep",
    "dieu kien tot nghiep",
    "yeu cau tot nghiep",
    "cong nhan tot nghiep",
    "dang ky xet tot nghiep",
    "ban giam hieu",
    "hieu truong",
    "truong khoa",
    "pho truong khoa",
    "ban chu nhiem khoa",
    "chu nhiem khoa",
    "lanh dao khoa",
    "nhan su khoa",
    "khoa mang",
    "mang may tinh",
    "truyen thong",
    "mang may tinh va truyen thong",
    "mang may tinh truyen thong",
    "mmt tt",
    "mmt",
    "nc uit",
    "cham toi dinh cao",
    "honors challenge",
    "honor",
    "honors",
    "ke hoach nam",
    "thong bao",
    "nsu crypto",
    "nsucrypto",
    "crypto",
    "olympic mat ma",
    "mat ma hoc",
)
_PDF_TEXT_CACHE: dict[str, str] = {}

_FACULTY_LEADERSHIP_MARKERS = (
    "truong khoa",
    "pho truong khoa",
    "ban chu nhiem khoa",
    "chu nhiem khoa",
    "lanh dao khoa",
    "nhan su khoa",
)
_NETWORK_FACULTY_MARKERS = (
    "khoa mang",
    "mang may tinh",
    "truyen thong",
    "mang may tinh va truyen thong",
    "mang may tinh truyen thong",
    "mmt tt",
    "mmt",
    "nc uit",
)


@dataclass
class SearchResult:
    title: str
    snippet: str
    href: str


class SearchProviderBlocked(RuntimeError):
    pass


def _is_external_http_url(href: str) -> bool:
    if not href.startswith(("http://", "https://")):
        return False
    host = urlparse(href).netloc.lower()
    return (
        "google." not in host
        and not host.endswith(".google.com")
        and "duckduckgo." not in host
        and not host.endswith(".duckduckgo.com")
    )


def _unwrap_google_url(href: str) -> str:
    parsed = urlparse(href or "")
    host = parsed.netloc.lower()
    if "google." not in host and not host.endswith(".google.com"):
        return href or ""
    if parsed.path == "/url":
        qs = parse_qs(parsed.query)
        if qs.get("q"):
            return unquote(qs["q"][0])
    return href or ""


def _unwrap_duckduckgo_url(href: str) -> str:
    parsed = urlparse(href or "")
    host = parsed.netloc.lower()
    if "duckduckgo." not in host and not host.endswith(".duckduckgo.com"):
        return href or ""
    qs = parse_qs(parsed.query)
    if qs.get("uddg"):
        return unquote(qs["uddg"][0])
    return href or ""


def _unwrap_search_url(href: str) -> str:
    return _unwrap_duckduckgo_url(_unwrap_google_url(href))


def _normalize_query(text: str) -> str:
    normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    compact = re.sub(r"[^a-z0-9]+", " ", stripped)
    return re.sub(r"\s+", " ", compact).strip()


def _contains_any(normalized: str, markers: tuple[str, ...]) -> bool:
    return any(marker in normalized for marker in markers)


def _has_site_filter(query: str) -> bool:
    return bool(re.search(r"\bsite\s*:", query, flags=re.IGNORECASE))


def _site_filters(query: str) -> list[str]:
    return [
        item.strip().strip("()").lower()
        for item in re.findall(r"\bsite\s*:\s*([^\s)]+)", query, flags=re.IGNORECASE)
    ]


def _has_priority_site_filter(query: str) -> bool:
    lowered = query.lower()
    return any(f"site:{domain}" in lowered or domain in lowered for domain in _UIT_PRIORITY_DOMAINS)


def _has_non_priority_site_filter(query: str) -> bool:
    return any(site and site not in _UIT_PRIORITY_DOMAINS for site in _site_filters(query))


def _is_uit_context_query(query: str) -> bool:
    normalized = _normalize_query(query)
    if "uit" not in normalized and _contains_any(normalized, _OTHER_SCHOOL_MARKERS):
        return False
    if _contains_any(normalized, _UIT_QUERY_MARKERS):
        return True
    lowered = query.lower()
    return any(domain in lowered for domain in _UIT_GENERAL_DOMAINS)


def _is_network_faculty_leadership_query(query: str) -> bool:
    normalized = _normalize_query(query)
    if "uit" not in normalized and _contains_any(normalized, _OTHER_SCHOOL_MARKERS):
        return False
    return _contains_any(normalized, _FACULTY_LEADERSHIP_MARKERS) and _contains_any(
        normalized,
        _NETWORK_FACULTY_MARKERS,
    )


def _is_network_faculty_staff_query(query: str) -> bool:
    normalized = _normalize_query(query)
    if "uit" not in normalized and _contains_any(normalized, _OTHER_SCHOOL_MARKERS):
        return False
    return _contains_any(normalized, ("giang vien", "doi ngu giang vien", "nhan su", "thay co")) and _contains_any(
        normalized,
        _NETWORK_FACULTY_MARKERS,
    )


def _is_information_security_curriculum_query(query: str) -> bool:
    normalized = _normalize_query(query)
    if "uit" not in normalized and _contains_any(normalized, _OTHER_SCHOOL_MARKERS):
        return False
    if "an toan thong tin" not in normalized and "attt" not in normalized:
        return False
    return _contains_any(
        normalized,
        (
            "mon chuyen nganh",
            "chuyen nganh",
            "mon hoc",
            "hoc phan",
            "chuong trinh dao tao",
            "ctdt",
        ),
    )


def _is_honors_challenge_query(query: str) -> bool:
    normalized = _normalize_query(query)
    if "uit" not in normalized and _contains_any(normalized, _OTHER_SCHOOL_MARKERS):
        return False
    return _contains_any(
        normalized,
        (
            "honor",
            "honors",
            "honors challenge",
            "cham toi dinh cao",
            "cham den dinh cao",
            "sinh vien tai nang",
        ),
    )


def _strip_site_filters(query: str) -> str:
    stripped = re.sub(r"\bsite\s*:\s*[^\s)]+", " ", query, flags=re.IGNORECASE)
    stripped = re.sub(r"\bOR\b", " ", stripped, flags=re.IGNORECASE)
    stripped = stripped.replace("(", " ").replace(")", " ")
    return re.sub(r"\s+", " ", stripped).strip()


def _uit_priority_query(query: str) -> str:
    site_filter = " OR ".join(f"site:{domain}" for domain in _UIT_PRIORITY_DOMAINS)
    terms = _strip_site_filters(query)
    return f"({site_filter}) {terms or query}"


def _uit_broad_query(query: str) -> str:
    terms = _strip_site_filters(query)
    return f"site:uit.edu.vn {terms or query}"


def _nsucrypto_queries(query: str) -> list[str]:
    normalized = _normalize_query(query)
    if "nsucrypto" not in normalized and "nsu crypto" not in normalized:
        return []
    years = re.findall(r"\b20\d{2}\b", query) or [str(datetime.now().year)]
    queries: list[str] = []
    for year in years:
        queries.extend(
            [
                f"(site:daa.uit.edu.vn OR site:oep.uit.edu.vn OR site:ctsv.uit.edu.vn) NSUCRYPTO {year} UIT",
                f"site:uit.edu.vn NSUCRYPTO {year} UIT",
                f"site:nc.uit.edu.vn NSUCRYPTO {year} UIT",
                f"site:inseclab.uit.edu.vn NSUCRYPTO {year} UIT",
                f"NSUCRYPTO {year} UIT đạt giải",
            ]
        )
    return queries


def _network_faculty_leadership_queries(query: str) -> list[str]:
    if not _is_network_faculty_leadership_query(query):
        return []
    return [
        'site:nc.uit.edu.vn "Ban chủ nhiệm khoa" "Trưởng khoa"',
        'site:nc.uit.edu.vn "Khoa Mạng máy tính và Truyền thông" "Trưởng khoa"',
        'site:nc.uit.edu.vn/ban-chu-nhiem-khoa "Trưởng khoa" "Phó Trưởng khoa"',
    ]


def _graduation_requirement_queries(query: str) -> list[str]:
    normalized = _normalize_query(query)
    if not _contains_any(
        normalized,
        (
            "tot nghiep",
            "xet tot nghiep",
            "dieu kien tot nghiep",
            "yeu cau tot nghiep",
            "cong nhan tot nghiep",
            "dang ky xet tot nghiep",
        ),
    ):
        return []
    if "uit" not in normalized and _contains_any(normalized, _OTHER_SCHOOL_MARKERS):
        return []
    return [
        'site:student.uit.edu.vn "xét tốt nghiệp" "điều kiện"',
        'site:daa.uit.edu.vn "điều kiện tốt nghiệp" UIT',
        'site:student.uit.edu.vn "đăng ký xét tốt nghiệp" UIT',
        'site:uit.edu.vn "điều kiện tốt nghiệp" "UIT"',
    ]


def _network_faculty_staff_queries(query: str) -> list[str]:
    if not _is_network_faculty_staff_query(query):
        return []
    return [
        'site:nc.uit.edu.vn/giang-vien "Họ tên" "Chức danh" "Bộ môn"',
        'site:nc.uit.edu.vn "Giảng viên" "Khoa Mạng máy tính và Truyền thông"',
    ]


def _information_security_curriculum_queries(query: str) -> list[str]:
    if not _is_information_security_curriculum_query(query):
        return []
    return [
        'site:daa.uit.edu.vn/content/cu-nhan-nganh-toan-thong-tin-ap-dung-tu-khoa-19-2024 "3.4.2" "Nhóm các môn học chuyên ngành"',
        'site:daa.uit.edu.vn "Cử nhân ngành An toàn Thông tin" "Nhóm các môn học chuyên ngành"',
        'site:oep.uit.edu.vn "An toàn Thông tin" "Chuyên ngành"',
    ]


def _honors_challenge_queries(query: str) -> list[str]:
    if not _is_honors_challenge_query(query):
        return []
    years = re.findall(r"\b20\d{2}\b", query) or [str(datetime.now().year)]
    queries: list[str] = []
    for year in years:
        queries.extend(
            [
                f'site:oep.uit.edu.vn "Kết quả dự kiến" "Sinh viên tài năng chạm tới đỉnh cao" "{year}"',
                f'site:oep.uit.edu.vn "UIT Honors Challenge" "{year}"',
                f'site:oep.uit.edu.vn "chạm tới đỉnh cao" "{year}"',
            ]
        )
    return queries


def _known_uit_results(query: str) -> list[SearchResult]:
    results: list[SearchResult] = []
    if _is_network_faculty_leadership_query(query):
        results.append(
            SearchResult(
                title="BAN CHỦ NHIỆM KHOA - UIT.NC",
                snippet="Trang chính thức Ban Chủ nhiệm Khoa Mạng máy tính và Truyền thông UIT.",
                href="https://nc.uit.edu.vn/ban-chu-nhiem-khoa",
            )
        )
    if _is_network_faculty_staff_query(query):
        results.append(
            SearchResult(
                title="Giảng viên - Khoa Mạng máy tính và Truyền thông UIT",
                snippet="Danh sách giảng viên chính thức của Khoa Mạng máy tính và Truyền thông UIT.",
                href="https://nc.uit.edu.vn/giang-vien",
            )
        )
    if _is_information_security_curriculum_query(query):
        results.append(
            SearchResult(
                title="Cử nhân ngành An toàn Thông tin (Áp dụng từ khóa 19 - 2024)",
                snippet="Chương trình đào tạo chính thức trên Cổng thông tin đào tạo UIT, gồm nhóm môn học chuyên ngành.",
                href="https://daa.uit.edu.vn/content/cu-nhan-nganh-toan-thong-tin-ap-dung-tu-khoa-19-2024",
            )
        )
    if _is_honors_challenge_query(query):
        results.extend(
            [
                SearchResult(
                    title='[HB] - Kết quả dự kiến của GT "Sinh viên tài năng chạm tới đỉnh cao", đợt 02 năm 2025',
                    snippet="Danh sách sinh viên dự kiến nhận giải thưởng UIT Honors Challenge đợt 02 năm 2025.",
                    href="https://oep.uit.edu.vn/vi/hb-ket-qua-du-kien-cua-gt-sinh-vien-tai-nang-cham-toi-dinh-cao-dot-02-nam-2025",
                ),
                SearchResult(
                    title='[HB] - Kết quả dự kiến của GT "Sinh viên tài năng chạm tới đỉnh cao", đợt 01 năm 2025',
                    snippet="Danh sách sinh viên dự kiến nhận giải thưởng UIT Honors Challenge đợt 01 năm 2025.",
                    href="https://oep.uit.edu.vn/vi/hb-ket-qua-du-kien-cua-gt-sinh-vien-tai-nang-cham-toi-dinh-cao-dot-01-nam-2025",
                ),
            ]
        )
    return results


def _expanded_queries(query: str) -> list[str]:
    normalized = _normalize_query(query)
    queries: list[str] = []
    should_prioritize_uit = _is_uit_context_query(query)

    queries.extend(_nsucrypto_queries(query))
    queries.extend(_network_faculty_leadership_queries(query))
    queries.extend(_graduation_requirement_queries(query))
    queries.extend(_network_faculty_staff_queries(query))
    queries.extend(_information_security_curriculum_queries(query))
    queries.extend(_honors_challenge_queries(query))

    if _is_honors_challenge_query(query):
        explicit_years = re.findall(r"\b20\d{2}\b", query)
        candidate_years = explicit_years or [str(datetime.now().year - 1), str(datetime.now().year)]
        for year in candidate_years:
            queries.append(f'site:oep.uit.edu.vn "HB" "Kết quả dự kiến" "chạm tới đỉnh cao" "{year}"')
        queries.append('site:oep.uit.edu.vn "Kết quả dự kiến" "chạm tới đỉnh cao"')

    if should_prioritize_uit and (
        not _has_priority_site_filter(query) or not _has_site_filter(query) or _has_non_priority_site_filter(query)
    ):
        queries.append(_uit_priority_query(query))

    if should_prioritize_uit:
        queries.append(_uit_broad_query(query))

    queries.append(query)

    unique: list[str] = []
    seen: set[str] = set()
    for item in queries:
        key = _normalize_query(item)
        if item and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    opts = Options()
    opts.binary_location = _CHROMIUM_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-images")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(f"--user-agent={_USER_AGENT}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    svc = Service(executable_path=_CHROMEDRIVER_BIN, log_output=os.devnull)
    driver = webdriver.Chrome(service=svc, options=opts)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"},
        )
    except Exception:
        pass
    return driver


def _google_is_blocked(driver) -> bool:
    current_url = (getattr(driver, "current_url", "") or "").lower()
    if "/sorry/" in current_url:
        return True
    try:
        body = str(driver.execute_script("return document.body ? document.body.innerText : ''") or "").lower()
    except Exception:
        return False
    return any(marker in body for marker in _GOOGLE_BLOCK_MARKERS)


def _search_google_sync(query: str, max_results: int) -> list[SearchResult]:
    from selenium.webdriver.support.ui import WebDriverWait

    driver = None
    try:
        fast_mode = max_results <= 2
        driver = _make_driver()
        requested = min(max(max_results * 3, 10), 20)
        driver.get(f"{_GOOGLE_SEARCH_URL}?q={quote_plus(query)}&hl=vi&num={requested}&udm=14")

        wait = WebDriverWait(driver, 6 if fast_mode else 12)
        wait.until(lambda item: item.execute_script("return document.readyState") == "complete")
        time.sleep(0.2 if fast_mode else 0.8)
        if _google_is_blocked(driver):
            raise SearchProviderBlocked("Google đang yêu cầu xác minh CAPTCHA")

        raw_results = driver.execute_script(
            """
            const anchors = Array.from(document.querySelectorAll("a[href]"));
            return anchors.map((anchor) => {
              const h3 = anchor.querySelector("h3");
              const title = ((h3 && h3.innerText) || anchor.innerText || "").trim();
              const container = anchor.closest("div.MjjYud, div.g, div[data-sokoban-container], div");
              let snippet = "";
              if (container) {
                const candidates = Array.from(container.querySelectorAll(".VwiC3b, .IsZvec, span, div"))
                  .map((node) => (node.innerText || "").trim())
                  .filter((text) => text && text !== title && text.length > 35 && !text.startsWith("http"));
                snippet = candidates[0] || "";
              }
              return { title, href: anchor.href || "", snippet };
            });
            """
        )
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for item in raw_results if isinstance(raw_results, list) else []:
            if len(results) >= max_results:
                break
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            href = _unwrap_search_url(str(item.get("href", "")).strip())

            if (not title and not snippet) or href in seen_urls or not _is_external_http_url(href):
                continue
            if not title:
                title = href
            seen_urls.add(href)
            results.append(SearchResult(title=title, snippet=snippet, href=href))

        return results

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def _search_duckduckgo_sync(query: str, max_results: int) -> list[SearchResult]:
    from selenium.webdriver.support.ui import WebDriverWait

    driver = None
    try:
        fast_mode = max_results <= 2
        driver = _make_driver()
        driver.get(f"{_DUCKDUCKGO_SEARCH_URL}?q={quote_plus(query)}&kl=vn-vi")

        wait = WebDriverWait(driver, 5 if fast_mode else 10)
        wait.until(lambda item: item.execute_script("return document.readyState") == "complete")
        time.sleep(0.2 if fast_mode else 0.6)

        raw_results = driver.execute_script(
            """
            const rows = Array.from(document.querySelectorAll(".result, .web-result"));
            return rows.map((row) => {
              const anchor = row.querySelector("a.result__a, h2 a, a[href]");
              const snippetNode = row.querySelector(".result__snippet, .result__body, .result__extras__url, .snippet");
              return {
                title: ((anchor && anchor.innerText) || "").trim(),
                href: (anchor && anchor.href) || "",
                snippet: ((snippetNode && snippetNode.innerText) || "").trim(),
              };
            });
            """
        )
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for item in raw_results if isinstance(raw_results, list) else []:
            if len(results) >= max_results:
                break
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            href = _unwrap_search_url(str(item.get("href", "")).strip())

            if (not title and not snippet) or href in seen_urls or not _is_external_http_url(href):
                continue
            if not title:
                title = href
            seen_urls.add(href)
            results.append(SearchResult(title=title, snippet=snippet, href=href))

        return results
    except Exception as exc:
        logger.warning("[web_search] DuckDuckGo fallback thất bại với query '%s': %s", query, exc)
        return []
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def _fallback_enabled() -> bool:
    value = os.environ.get("WEB_SEARCH_FALLBACK_DUCKDUCKGO", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _search_single_query_sync(query: str, max_results: int) -> list[SearchResult]:
    try:
        results = _search_google_sync(query, max_results)
        if results:
            return results
        logger.info("[web_search] Google không trả kết quả cho query '%s'", query)
    except SearchProviderBlocked as exc:
        logger.warning("[web_search] Google bị chặn với query '%s': %s", query, exc)
    except Exception as exc:
        logger.warning("[web_search] Google Selenium thất bại với query '%s': %s", query, exc)

    if not _fallback_enabled():
        return []

    logger.info("[web_search] Dùng DuckDuckGo fallback cho query '%s'", query)
    return _search_duckduckgo_sync(query, max_results)


def _merge_results(results: list[SearchResult], max_results: int) -> list[SearchResult]:
    merged: list[SearchResult] = []
    seen_urls: set[str] = set()
    for result in results:
        if len(merged) >= max_results:
            break
        if result.href in seen_urls:
            continue
        seen_urls.add(result.href)
        merged.append(result)
    return merged


def _search_sync(query: str, max_results: int) -> list[SearchResult]:
    collected: list[SearchResult] = _known_uit_results(query)
    if collected:
        return _merge_results(collected, max_results)
    for expanded_query in _expanded_queries(query):
        collected.extend(_search_single_query_sync(expanded_query, max_results))
        if len(_merge_results(collected, max_results)) >= max_results:
            break
    return _merge_results(collected, max_results)


def _clean_page_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _clean_multiline_page_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines()]
    return "\n".join(line for line in lines if line)


def _text_window(text: str, markers: tuple[str, ...], char_limit: int, before: int = 250) -> str:
    lowered = text.lower()
    start = -1
    for marker in markers:
        index = lowered.find(marker.lower())
        if index >= 0 and (start < 0 or index < start):
            start = index
    if start < 0:
        return text[:char_limit]
    start = max(0, start - before)
    return text[start : start + char_limit]


def _faculty_table_excerpt(html: str, char_limit: int) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return ""

    lines = ["Danh sách giảng viên Khoa Mạng máy tính và Truyền thông UIT:"]
    for row in table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) < 5:
            continue
        name = cells[1]
        title = cells[2]
        department = cells[3]
        email_match = re.search(r"[\w.+-]+@[\w.-]+", cells[4])
        email = email_match.group(0) if email_match else ""
        if not name:
            continue
        contact = f" - {email}" if email else ""
        lines.append(f"- {name} | {title} | {department}{contact}")
    return "\n".join(lines)[:char_limit]


def _targeted_html_excerpt(html: str, url: str, query: str, char_limit: int) -> str:
    normalized_query = _normalize_query(query)
    lowered_url = url.lower()

    if "nc.uit.edu.vn/giang-vien" in lowered_url and _is_network_faculty_staff_query(query):
        excerpt = _faculty_table_excerpt(html, char_limit)
        if excerpt:
            return excerpt

    multiline_text = _clean_multiline_page_text(html)
    if "cu-nhan-nganh-toan-thong-tin-ap-dung-tu-khoa-19-2024" in lowered_url and _is_information_security_curriculum_query(query):
        return _text_window(
            multiline_text,
            (
                "3.4.2",
                "Nhóm các môn học chuyên ngành",
                "Nhóm các môn học chuyên ngành",
                "Sinh viên chọn 3 môn",
            ),
            char_limit,
        )

    if "cham-toi-dinh-cao-dot-" in lowered_url and _is_honors_challenge_query(query):
        return _text_window(
            multiline_text,
            (
                "DANH SÁCH SINH VIÊN DỰ KIẾN",
                "NHẬN GIẢI THƯỞNG",
                "NGÀNH KHOA HỌC MÁY TÍNH",
            ),
            char_limit,
            before=80,
        )

    if _contains_any(normalized_query, ("chuyen nganh", "giang vien", "honor", "honors", "cham toi dinh cao")):
        return _text_window(
            multiline_text,
            (
                "Nhóm các môn học chuyên ngành",
                "Nhóm các môn học chuyên ngành",
                "DANH SÁCH SINH VIÊN",
                "Họ tên",
                "Giảng viên",
            ),
            char_limit,
        )

    return ""


def _should_fetch_pdf_attachments(result: SearchResult, page_text: str) -> bool:
    haystack = f"{result.title} {result.snippet} {page_text[:1200]}".lower()
    markers = (
        "file đính kèm",
        "file dinh kem",
        "quyết định",
        "quyet dinh",
        "danh sách",
        "danh sach",
        "khen thưởng",
        "khen thuong",
        "nsucrypto",
        "mật mã học",
        "mat ma hoc",
        "pdf đính kèm",
        "pdf dinh kem",
    )
    return any(marker in haystack for marker in markers)


def _is_pdf_url(url: str) -> bool:
    lowered = url.lower()
    return urlparse(url).path.lower().endswith(".pdf") or ".pdf?" in lowered


def _pdf_links_from_html(html: str, base_url: str, max_links: int = 2) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = urljoin(base_url, anchor.get("href", ""))
        if not _is_pdf_url(href) or href in seen:
            continue
        seen.add(href)
        links.append(href)
        if len(links) >= max_links:
            break
    return links


def _extract_pdf_bytes(pdf_bytes: bytes) -> str:
    from app.services.file_extraction_service import FileExtractionService

    with tempfile.TemporaryDirectory(prefix="studify-web-pdf-") as tmp:
        tmp_dir = Path(tmp)
        pdf_path = tmp_dir / "source.pdf"
        pdf_path.write_bytes(pdf_bytes)
        text, _used_ocr = FileExtractionService().extract_pdf_text(pdf_path, tmp_dir / "ocr")
        return text


async def _fetch_pdf_excerpt(client: httpx.AsyncClient, pdf_url: str, char_limit: int) -> str:
    try:
        if pdf_url in _PDF_TEXT_CACHE:
            return f"PDF đính kèm ({pdf_url}): {_PDF_TEXT_CACHE[pdf_url][:char_limit]}"
        response = await client.get(pdf_url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not _is_pdf_url(pdf_url):
            return ""
        pdf_bytes = response.content
        if not pdf_bytes or len(pdf_bytes) > 20_000_000:
            return ""
        text = await asyncio.to_thread(_extract_pdf_bytes, pdf_bytes)
        if not text:
            return ""
        _PDF_TEXT_CACHE[pdf_url] = text
        return f"PDF đính kèm ({pdf_url}): {text[:char_limit]}"
    except Exception as exc:
        logger.debug("[web_search] Không đọc được PDF %s: %s", pdf_url, exc)
        return ""


async def _fetch_page_excerpt(
    client: httpx.AsyncClient,
    result: SearchResult,
    semaphore: asyncio.Semaphore,
    char_limit: int,
    query: str,
) -> str:
    if not result.href.startswith(("http://", "https://")):
        return ""

    async with semaphore:
        try:
            response = await client.get(result.href)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" in content_type or _is_pdf_url(result.href):
                return await _fetch_pdf_excerpt(client, result.href, char_limit)
            if "text/html" not in content_type and "text/plain" not in content_type:
                return ""
            targeted = _targeted_html_excerpt(response.text, result.href, query, char_limit)
            if targeted:
                return targeted
            text = _clean_page_text(response.text)
            pdf_links = _pdf_links_from_html(response.text, result.href) if _should_fetch_pdf_attachments(result, text) else []
            pdf_sections: list[str] = []
            for pdf_url in pdf_links:
                pdf_excerpt = await _fetch_pdf_excerpt(client, pdf_url, char_limit)
                if pdf_excerpt:
                    pdf_sections.append(pdf_excerpt)
            if pdf_sections:
                base_limit = max(700, char_limit // 4)
                combined = " ".join([*pdf_sections, f"Nội dung trang: {text[:base_limit]}"])
                return combined[:char_limit]
            return text[:char_limit]
        except Exception as exc:
            logger.debug("[web_search] Không đọc được trang %s: %s", result.href, exc)
            return ""


async def _fetch_page_excerpts(results: list[SearchResult], fast_mode: bool, query: str) -> list[str]:
    if not results:
        return []

    concurrency = 2 if fast_mode else min(5, len(results))
    timeout = httpx.Timeout(4.0 if fast_mode else 8.0, connect=2.0)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.8"}
    char_limit = 12000 if (not fast_mode or _known_uit_results(query)) else 4500
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, limits=limits) as client:
        tasks = [_fetch_page_excerpt(client, result, semaphore, char_limit, query) for result in results]
        return await asyncio.gather(*tasks)


def _format_results(query: str, results: list[SearchResult], excerpts: list[str]) -> str:
    if not results:
        return (
            f"Không tìm thấy kết quả nào cho: {query}\n"
            "Nếu câu hỏi vẫn có thể trả lời bằng kiến thức nền của model, hãy trả lời trực tiếp, "
            "nói rõ phần đó chưa xác minh được bằng web search và không yêu cầu người dùng gửi link trừ khi thật sự cần."
        )

    lines: list[str] = [f"Kết quả tìm kiếm cho: {query}\n"]
    for index, result in enumerate(results, start=1):
        excerpt = excerpts[index - 1] if index - 1 < len(excerpts) else ""
        lines.append(f"[{index}] {result.title or result.href}")
        if result.snippet:
            lines.append(f"    Tóm tắt tìm kiếm: {result.snippet[:400]}")
        if excerpt:
            lines.append(f"    Nội dung trang: {excerpt}")
        if result.href:
            lines.append(f"    Nguồn: {result.href}")
        lines.append("")
    return "\n".join(lines).strip()


class WebSearchService:
    """Tìm kiếm web qua Google bằng headless Chromium, trả về text cho LLM."""

    async def search(self, query: str, max_results: int = 5) -> str:
        loop = asyncio.get_running_loop()
        fn = partial(_search_sync, query, max_results)
        results = await loop.run_in_executor(None, fn)
        excerpts = await _fetch_page_excerpts(results, fast_mode=max_results <= 2, query=query)
        return _format_results(query, results, excerpts)
