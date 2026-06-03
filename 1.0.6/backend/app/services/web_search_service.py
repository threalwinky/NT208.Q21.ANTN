"""
Web search service – dùng Selenium + headless Chromium.

Tìm kiếm DuckDuckGo qua trình duyệt thật để tránh bị chặn rate-limit của API text.
Sau khi có danh sách kết quả, fetch nhiều trang nguồn song song bằng async HTTP để tăng tốc.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from functools import partial
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger(__name__)

_CHROMIUM_BIN = os.environ.get("CHROMIUM_BIN", "/usr/bin/chromium")
_CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_BIN", "/usr/bin/chromedriver")

_DDGURL = "https://duckduckgo.com/"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class SearchResult:
    title: str
    snippet: str
    href: str


def _is_external_http_url(href: str) -> bool:
    if not href.startswith(("http://", "https://")):
        return False
    host = urlparse(href).netloc.lower()
    return host not in {"duckduckgo.com", "www.duckduckgo.com"}


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
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(f"--user-agent={_USER_AGENT}")

    svc = Service(executable_path=_CHROMEDRIVER_BIN, log_output=os.devnull)
    return webdriver.Chrome(service=svc, options=opts)


def _search_sync(query: str, max_results: int) -> list[SearchResult]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    driver = None
    try:
        fast_mode = max_results <= 2
        driver = _make_driver()
        driver.get(f"{_DDGURL}?q={quote_plus(query)}&ia=web")

        wait = WebDriverWait(driver, 6 if fast_mode else 12)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='result']")))
        time.sleep(0.2 if fast_mode else 0.8)

        result_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='result']")
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for elem in result_elements:
            if len(results) >= max_results:
                break
            try:
                title_el = elem.find_element(By.CSS_SELECTOR, "h2")
                title = title_el.text.strip()
            except Exception:
                title = ""

            try:
                snippet_el = elem.find_element(By.CSS_SELECTOR, "[data-result='snippet']")
                snippet = snippet_el.text.strip()
            except Exception:
                snippet = ""

            try:
                link_el = elem.find_element(By.CSS_SELECTOR, "[data-testid='result-title-a']")
            except Exception:
                try:
                    link_el = elem.find_element(By.CSS_SELECTOR, "h2 a[href]")
                except Exception:
                    link_el = None

            try:
                href = link_el.get_attribute("href") if link_el is not None else ""
                href = href or ""
                if "uddg=" in href:
                    from urllib.parse import parse_qs, unquote

                    qs = parse_qs(urlparse(href).query)
                    href = unquote(qs.get("uddg", [href])[0])
            except Exception:
                href = ""

            if (not title and not snippet) or href in seen_urls or not _is_external_http_url(href):
                continue
            seen_urls.add(href)
            results.append(SearchResult(title=title, snippet=snippet, href=href))

        return results

    except Exception as exc:
        logger.warning("[web_search] Selenium thất bại với query '%s': %s", query, exc)
        return []
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def _clean_page_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


async def _fetch_page_excerpt(
    client: httpx.AsyncClient,
    result: SearchResult,
    semaphore: asyncio.Semaphore,
    char_limit: int,
) -> str:
    if not result.href.startswith(("http://", "https://")):
        return ""

    async with semaphore:
        try:
            response = await client.get(result.href)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return ""
            text = _clean_page_text(response.text)
            return text[:char_limit]
        except Exception as exc:
            logger.debug("[web_search] Không đọc được trang %s: %s", result.href, exc)
            return ""


async def _fetch_page_excerpts(results: list[SearchResult], fast_mode: bool) -> list[str]:
    if not results:
        return []

    concurrency = 2 if fast_mode else min(5, len(results))
    timeout = httpx.Timeout(4.0 if fast_mode else 8.0, connect=2.0)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.8"}
    char_limit = 900 if fast_mode else 1600
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, limits=limits) as client:
        tasks = [_fetch_page_excerpt(client, result, semaphore, char_limit) for result in results]
        return await asyncio.gather(*tasks)


def _format_results(query: str, results: list[SearchResult], excerpts: list[str]) -> str:
    if not results:
        return f"Không tìm thấy kết quả nào cho: {query}"

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
    """Tìm kiếm web qua DuckDuckGo bằng headless Chromium, trả về text cho LLM."""

    async def search(self, query: str, max_results: int = 5) -> str:
        loop = asyncio.get_running_loop()
        fn = partial(_search_sync, query, max_results)
        results = await loop.run_in_executor(None, fn)
        excerpts = await _fetch_page_excerpts(results, fast_mode=max_results <= 2)
        return _format_results(query, results, excerpts)
