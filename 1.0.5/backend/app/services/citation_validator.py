from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.schemas.chat import CitationItem


@dataclass(slots=True)
class CitationValidationResult:
    answer: str
    removed_urls: list[str]


class CitationValidator:
    markdown_link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
    bare_url_pattern = re.compile(r"(?<!\()https?://[^\s)]+")

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url.strip())
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"

    def _allowed(self, citations: list[CitationItem]) -> set[str]:
        return {self._normalize_url(item.url) for item in citations if item.url}

    def clean_answer(self, answer: str, citations: list[CitationItem]) -> CitationValidationResult:
        allowed_urls = self._allowed(citations)
        removed: list[str] = []

        def markdown_replacer(match: re.Match[str]) -> str:
            label, url = match.group(1), match.group(2)
            if self._normalize_url(url) in allowed_urls:
                return match.group(0)
            removed.append(url)
            return label

        cleaned = self.markdown_link_pattern.sub(markdown_replacer, answer or "")

        def bare_replacer(match: re.Match[str]) -> str:
            url = match.group(0).rstrip(".,;")
            suffix = match.group(0)[len(url) :]
            if self._normalize_url(url) in allowed_urls:
                return match.group(0)
            removed.append(url)
            return suffix

        cleaned = self.bare_url_pattern.sub(bare_replacer, cleaned)
        return CitationValidationResult(answer=cleaned.strip(), removed_urls=list(dict.fromkeys(removed)))
