from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone


class KnowledgeMetadataService:
    PROGRAM_PATTERNS = {
        "standard": ["chuong trinh chuan", "dai tra", "ctdtr"],
        "vietnam-japan": ["viet nhat", "chinh quy viet nhat"],
        "honors": ["tai nang", "cu nhan tai nang", "ky su tai nang", "cttn"],
        "high-quality": ["chat luong cao", "clc", "ctclc"],
        "advanced": ["tien tien", "cttt"],
        "bcu": ["bcu", "birmingham city"],
        "uon": ["uon", "uon programme"],
    }

    DOCUMENT_KIND_HINTS = {
        "ENGLISH_REQUIREMENT": ["chuan dau ra", "ngoai ngu", "tieng anh", "toeic", "ielts", "vstep", "vnu ept"],
        "TUITION": ["hoc phi", "thu hoc phi", "muc thu hoc phi", "gia han hoc phi"],
        "GRADUATION": ["xet tot nghiep", "tot nghiep", "trao bang"],
        "PROCEDURE": ["giay xac nhan", "giay gioi thieu", "bao luu", "tam ngung", "thoi hoc", "thu tuc"],
        "ANNUAL_PLAN": ["ke hoach dao tao nam hoc", "ke hoach nam", "nghi he", "hoc ky he", "khai giang", "tet am lich"],
        "ACADEMIC_WARNING": ["canh bao hoc vu", "canh bao hoc tap", "canh bao sinh vien", "xu ly hoc vu"],
        "REGISTRATION": ["dang ky hoc phan", "xac nhan dkhp", "dkhp"],
        "CURRICULUM": ["chuong trinh dao tao", "ctdt", "khung chuong trinh", "ke hoach hoc tap"],
        "SCHOLARSHIP": ["hoc bong", "kkht", "khuyen khich hoc tap"],
    }

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
        stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        compact = re.sub(r"[^a-z0-9/.-]+", " ", stripped)
        return re.sub(r"\s+", " ", compact).strip()

    def _contains_pattern(self, haystack: str, pattern: str) -> bool:
        escaped = re.escape(pattern)
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", haystack) is not None

    def _extract_school_years(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        years = {
            f"{start}-{end}"
            for start, end in re.findall(r"\b(20\d{2})\s*[-/]\s*(20\d{2})\b", normalized)
            if int(end) == int(start) + 1
        }
        return sorted(years)

    def _extract_dates(self, text: str) -> list[datetime]:
        normalized = self._normalize(text)
        dates: list[datetime] = []
        for day, month, year in re.findall(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", normalized):
            try:
                dates.append(datetime(int(year), int(month), int(day), tzinfo=timezone.utc))
            except ValueError:
                continue
        return sorted(set(dates))

    def _extract_programs(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        programs = [
            name
            for name, patterns in self.PROGRAM_PATTERNS.items()
            if any(self._contains_pattern(normalized, pattern) for pattern in patterns)
        ]
        return sorted(set(programs))

    def _expand_year_range(self, start: int, end: int) -> list[str]:
        if end < start or end - start > 8:
            return []
        return [str(year) for year in range(start, end + 1)]

    def _extract_cohorts(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        cohorts: set[str] = set()

        for year in re.findall(r"\bk\s*(20\d{2})\b", normalized):
            cohorts.add(year)

        for year in re.findall(r"\bkhoa\s*(20\d{2})\b", normalized):
            cohorts.add(year)

        for start, end in re.findall(r"\bkhoa\s*(20\d{2})\s*(?:-|den)\s*(20\d{2})\b", normalized):
            cohorts.update(self._expand_year_range(int(start), int(end)))

        for year in re.findall(r"\bkhoa tuyen nam\s*(20\d{2})\b", normalized):
            cohorts.add(year)

        return sorted(cohorts)

    def _infer_document_kind(self, text: str) -> str:
        normalized = self._normalize(text)
        for kind, hints in self.DOCUMENT_KIND_HINTS.items():
            if any(hint in normalized for hint in hints):
                return kind
        return "OTHER"

    def _freshness_bucket(
        self,
        *,
        school_years: list[str],
        effective_from: datetime | None,
        effective_to: datetime | None,
        updated_source_at: datetime | None,
    ) -> str:
        now = datetime.now(timezone.utc)
        current_year = now.year

        if effective_to and effective_to < now:
            return "ARCHIVED"
        if effective_from and effective_from > now:
            return "UPCOMING"

        for school_year in school_years:
            try:
                start, end = [int(part) for part in school_year.split("-", maxsplit=1)]
            except ValueError:
                continue
            if start <= current_year <= end:
                return "CURRENT"

        if updated_source_at and (now - updated_source_at).days <= 180:
            return "CURRENT"
        return "REFERENCE"

    def build_metadata(
        self,
        *,
        title: str,
        text: str,
        tags: list[str] | None = None,
        published_at: datetime | None = None,
        updated_source_at: datetime | None = None,
        url: str | None = None,
    ) -> dict:
        haystack = " ".join(filter(None, [title, text, " ".join(tags or []), url or ""]))
        school_years = self._extract_school_years(haystack)
        dates = self._extract_dates(text)
        document_kind = self._infer_document_kind(haystack)
        effective_from = dates[0] if dates else published_at
        effective_to = dates[-1] if len(dates) >= 2 else None
        applies_to_programs = self._extract_programs(haystack)
        applies_to_cohorts = self._extract_cohorts(haystack)
        freshness_bucket = self._freshness_bucket(
            school_years=school_years,
            effective_from=effective_from,
            effective_to=effective_to,
            updated_source_at=updated_source_at,
        )

        return {
            "document_kind": document_kind,
            "school_years": school_years,
            "effective_from": effective_from.isoformat() if effective_from else None,
            "effective_to": effective_to.isoformat() if effective_to else None,
            "applies_to_programs": applies_to_programs,
            "applies_to_cohorts": applies_to_cohorts,
            "freshness_bucket": freshness_bucket,
            "parsed_dates": [item.isoformat() for item in dates[:12]],
        }
