from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.schemas.chat import CitationItem


@dataclass(slots=True)
class CitationValidationResult:
    answer: str
    removed_urls: list[str]


# Domain chính thức của UIT – URL thuộc các domain này được giữ lại dù không
# có trong danh sách citations (vì web_search bị giới hạn ở site UIT chính thức,
# nên đây là nguồn thật, không phải bịa). Nhờ vậy câu trả lời lấy từ web search
# vẫn còn mục "Nguồn tham khảo".
_OFFICIAL_UIT_SUFFIXES = ("uit.edu.vn",)


class CitationValidator:
    markdown_link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
    bare_url_pattern = re.compile(r"(?<!\()https?://[^\s)]+")

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url.strip())
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"

    def _allowed(self, citations: list[CitationItem]) -> set[str]:
        return {self._normalize_url(item.url) for item in citations if item.url}

    def _is_official_uit(self, url: str) -> bool:
        host = urlparse(url.strip()).netloc.lower().split(":")[0]
        return any(host == suffix or host.endswith("." + suffix) for suffix in _OFFICIAL_UIT_SUFFIXES)

    def clean_answer(self, answer: str, citations: list[CitationItem]) -> CitationValidationResult:
        allowed_urls = self._allowed(citations)
        removed: list[str] = []

        def is_kept(url: str) -> bool:
            return self._normalize_url(url) in allowed_urls or self._is_official_uit(url)

        def markdown_replacer(match: re.Match[str]) -> str:
            label, url = match.group(1), match.group(2)
            if is_kept(url):
                return match.group(0)
            removed.append(url)
            return label

        cleaned = self.markdown_link_pattern.sub(markdown_replacer, answer or "")

        def bare_replacer(match: re.Match[str]) -> str:
            url = match.group(0).rstrip(".,;")
            suffix = match.group(0)[len(url) :]
            if is_kept(url):
                return match.group(0)
            removed.append(url)
            return suffix

        cleaned = self.bare_url_pattern.sub(bare_replacer, cleaned)
        return CitationValidationResult(answer=cleaned.strip(), removed_urls=list(dict.fromkeys(removed)))
