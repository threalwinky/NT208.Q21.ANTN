from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.knowledge import CollectedDocument
from app.services.ollama_service import OllamaService
from app.services.qdrant_service import QdrantService


@dataclass
class RetrievedContext:
    document: CollectedDocument
    excerpt: str
    score: float


@dataclass
class CandidateContext:
    document: CollectedDocument
    excerpt: str
    vector_score: float = 0.0
    lexical_score: float = 0.0
    source_score: float = 0.0


class RagService:
    def __init__(self) -> None:
        self.ollama = OllamaService()
        self.qdrant = QdrantService()

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
        stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        compact = re.sub(r"[^a-z0-9]+", " ", stripped)
        return re.sub(r"\s+", " ", compact).strip()

    def _has_any(self, haystack: str, needles: list[str]) -> bool:
        return any(needle in haystack for needle in needles)

    def _query_years(self, text: str) -> set[str]:
        return set(re.findall(r"\b20\d{2}\b", self._normalize(text)))

    def _document_domain(self, document: CollectedDocument) -> str:
        if document.data_source and document.data_source.domain:
            return str(document.data_source.domain).lower()
        return urlparse(document.url or "").netloc.lower().removeprefix("www.")

    def _is_faculty_specific_query(self, normalized_query: str) -> bool:
        return self._has_any(
            normalized_query,
            [
                "khoa cong nghe phan mem",
                "ky thuat phan mem",
                "truyen thong da phuong tien",
                "khoa cong nghe thong tin",
                "khoa hoc du lieu",
                "khoa khoa hoc may tinh",
                "tri tue nhan tao",
                "khoa he thong thong tin",
                "thuong mai dien tu",
                "khoa mang may tinh",
                "an toan thong tin",
                "khoa ky thuat may tinh",
                "thiet ke vi mach",
                "se uit",
                "fit uit",
                "cs uit",
                "httt uit",
                "nc uit",
                "fce uit",
            ],
        )

    def _query_topics(self, query: str) -> set[str]:
        normalized_query = self._normalize(query)
        topics: set[str] = set()

        if self._has_any(
            normalized_query,
            [
                "tieng anh",
                "ngoai ngu",
                "chuan dau ra",
                "chuan qua trinh",
                "toeic",
                "ielts",
                "toefl",
                "vstep",
                "vnu ept",
                "chung chi",
            ],
        ):
            topics.add("english")

        if self._has_any(
            normalized_query,
            [
                "dang ky hoc phan",
                "dang ky hoc",
                "dkhp",
                "xac nhan dkhp",
                "hoc phan",
            ],
        ):
            topics.add("registration")

        if self._has_any(
            normalized_query,
            [
                "hoc phi",
                "thu hoc phi",
                "dong hoc phi",
                "mien giam hoc phi",
                "gia han hoc phi",
            ],
        ):
            topics.add("tuition")

        if self._has_any(
            normalized_query,
            [
                "hoc bong",
                "khuyen khich hoc tap",
                "kkht",
                "ngoai ngan sach",
                "xet hoc bong",
            ],
        ):
            topics.add("scholarship")

        if self._has_any(
            normalized_query,
            [
                "tot nghiep",
                "xet tot nghiep",
                "dieu kien tot nghiep",
                "ra truong",
                "khoa luan",
                "do an",
            ],
        ):
            topics.add("graduation")

        if self._has_any(
            normalized_query,
            [
                "giay xac nhan",
                "xac nhan sinh vien",
                "giay gioi thieu",
                "thu tuc",
                "bao luu",
                "tam ngung",
                "thoi hoc",
                "don tu",
                "chuyen nganh",
                "song nganh",
                "cong nhan tin chi",
            ],
        ):
            topics.add("procedure")

        if self._has_any(
            normalized_query,
            [
                "lich thi",
                "lich hoc",
                "thoi khoa bieu",
                "tkb",
                "giua ky",
                "cuoi ky",
                "lich dkhp",
                "dkhp",
            ],
        ):
            topics.add("schedule")

        if self._has_any(
            normalized_query,
            [
                "ke hoach nam",
                "ke hoach dao tao nam hoc",
                "lich nghi",
                "nghi he",
                "ve he",
                "hoc ky he",
                "hk he",
                "khai giang",
                "tet am lich",
            ],
        ):
            topics.add("annual_plan")

        if self._has_any(
            normalized_query,
            [
                "canh bao hoc vu",
                "canh bao hoc tap",
                "canh bao sinh vien",
                "xu ly hoc vu",
                "ket qua dang ky hoc phan",
                "ket qua hoc tap",
            ],
        ):
            topics.add("academic_warning")

        if self._has_any(
            normalized_query,
            [
                "ctdt",
                "chuong trinh dao tao",
                "ke hoach hoc tap",
                "khung chuong trinh",
                "hoc mon nao",
                "nganh hoc",
                "khoa 2025",
                "khoa 2024",
            ],
        ):
            topics.add("curriculum")

        if self._has_any(
            normalized_query,
            [
                "oep",
                "tai nang",
                "chat luong cao",
                "tien tien",
                "chuong trinh dac biet",
                "cttn",
                "ctclc",
                "cttt",
                "bcu",
                "uon",
            ],
        ):
            topics.add("special_program")

        return topics

    def _extract_tokens(self, query: str) -> list[str]:
        normalized_query = self._normalize(query)
        tokens = re.findall(r"[a-z0-9]+", normalized_query)
        topics = self._query_topics(query)
        if "dang ky hoc phan" in normalized_query:
            tokens.extend(["dkhp", "hocphan"])
        if "english" in topics:
            tokens.extend(["ngoai", "ngu", "chuan", "dau", "ra", "toeic", "ielts", "toefl", "vstep", "vnu", "ept"])
        if "special_program" in topics:
            tokens.extend(["oep", "cttt", "clc", "bcu", "uon"])
        if "scholarship" in topics:
            tokens.extend(["hoc", "bong", "kkht", "khuyen", "khich", "ngoai", "ngan", "sach"])
        if "tuition" in topics:
            tokens.extend(["hoc", "phi", "dong", "thu", "gia", "han"])
        if "graduation" in topics:
            tokens.extend(["tot", "nghiep", "xet", "ra", "truong"])
        if "procedure" in topics:
            tokens.extend(["giay", "xac", "nhan", "gioi", "thieu", "thu", "tuc", "bao", "luu", "tam", "ngung", "song", "nganh"])
        if "schedule" in topics:
            tokens.extend(["lich", "thi", "lich", "hoc", "thoi", "khoa", "bieu", "tkb", "dkhp"])
        if "annual_plan" in topics:
            tokens.extend(["ke", "hoach", "nam", "hoc", "nghi", "he", "hk", "he", "khai", "giang", "tet"])
        if "academic_warning" in topics:
            tokens.extend(["canh", "bao", "hoc", "vu", "hoc", "tap", "xu", "ly", "dkhp"])
        if "curriculum" in topics:
            tokens.extend(["ctdt", "chuong", "trinh", "dao", "tao", "hoc", "phan"])
        if "cong tac sinh vien" in normalized_query or "ctsv" in normalized_query:
            tokens.extend(["ctsv"])
        if "dao tao" in normalized_query or "daa" in normalized_query:
            tokens.extend(["daa"])
        if "cong sinh vien" in normalized_query or "student" in normalized_query:
            tokens.extend(["student"])
        if "khtc" in normalized_query or "ke hoach tai chinh" in normalized_query:
            tokens.extend(["khtc"])
        unique_tokens: list[str] = []
        seen_tokens: set[str] = set()
        for token in tokens:
            if len(token) < 3 or token in seen_tokens:
                continue
            seen_tokens.add(token)
            unique_tokens.append(token)
        return unique_tokens

    def _lexical_score(self, query: str, document: CollectedDocument, excerpt: str) -> float:
        normalized_query = self._normalize(query)
        tokens = self._extract_tokens(query)
        if not tokens:
            return 0.0

        title = self._normalize(document.title)
        body = self._normalize(" ".join(filter(None, [excerpt, document.summary or "", document.cleaned_content or ""])))
        title_hits = sum(1 for token in tokens if token in title)
        body_hits = sum(1 for token in tokens if token in body)
        title_ratio = min(1.0, title_hits / max(1, min(len(tokens), 4)))
        body_ratio = min(1.0, body_hits / max(1, len(tokens)))
        phrase_bonus = 0.15 if normalized_query and normalized_query in f"{title} {body}" else 0.0
        coverage_bonus = 0.2 if title_hits >= max(2, len(tokens) // 2) else 0.0
        official_bonus = 0.08 if document.is_official_uit else 0.0
        return (title_ratio * 0.7) + (body_ratio * 0.15) + phrase_bonus + coverage_bonus + official_bonus

    def _source_hint_score(self, query: str, document: CollectedDocument) -> float:
        normalized_query = self._normalize(query)
        topics = self._query_topics(query)
        query_years = self._query_years(query)
        haystack = self._normalize(
            " ".join(
                filter(
                    None,
                    [
                        document.title,
                        document.url,
                        document.group_name or "",
                        " ".join(document.tags or []),
                        document.summary or "",
                        (document.cleaned_content or "")[:1800],
                        json.dumps(document.vector_metadata or {}, ensure_ascii=False),
                    ],
                )
            )
        )
        score = 0.0
        document_domain = self._document_domain(document)
        faculty_specific_query = self._is_faculty_specific_query(normalized_query)
        critical_domains = {
            "uit.edu.vn",
            "daa.uit.edu.vn",
            "student.uit.edu.vn",
            "ctsv.uit.edu.vn",
            "khtc.uit.edu.vn",
            "oep.uit.edu.vn",
        }
        faculty_domains = {
            "se.uit.edu.vn",
            "fit.uit.edu.vn",
            "cs.uit.edu.vn",
            "httt.uit.edu.vn",
            "nc.uit.edu.vn",
            "fce.uit.edu.vn",
        }

        source_hints = {
            "oep": ["oep", "chuong trinh dac biet", "chuong trinh tien tien", "chat luong cao", "lien ket"],
            "ctsv": ["ctsv", "cong tac sinh vien"],
            "daa": ["daa", "dao tao", "hoc vu"],
            "student": ["student", "cong sinh vien", "portal sinh vien"],
            "khtc": ["khtc", "ke hoach tai chinh", "thanh toan hoc phi", "thu hoc phi"],
            "courses": ["courses", "moodle", "hoc truc tuyen"],
        }

        for query_hint, document_hints in source_hints.items():
            if query_hint not in normalized_query:
                continue
            if any(hint in haystack for hint in document_hints):
                score += 0.4

        if document.is_official_uit:
            score += 0.08

        if document_domain in critical_domains:
            score += 0.08
        if document_domain in faculty_domains and not faculty_specific_query and topics.intersection({"english", "registration", "tuition", "scholarship", "graduation", "procedure", "schedule", "annual_plan", "academic_warning"}):
            score -= 0.25
        if document_domain in faculty_domains and faculty_specific_query:
            score += 0.2

        if "dang ky hoc phan" in normalized_query and any(token in haystack for token in ["dang ky hoc phan", "dkhp"]):
            score += 0.25
        if "quy dinh" in normalized_query and any(token in haystack for token in ["quy dinh", "quy che"]):
            score += 0.15
        if "english" in topics:
            if self._has_any(
                haystack,
                [
                    "chuan qua trinh va chuan dau ra ngoai ngu",
                    "quy dinh dao tao ngoai ngu",
                    "chuan ngoai ngu xet tot nghiep",
                    "ngoai ngu",
                    "tieng anh",
                    "toeic",
                    "ielts",
                    "vnu ept",
                    "vstep",
                    "chuan dau ra",
                ],
            ):
                score += 0.55
            if self._has_any(
                haystack,
                [
                    "141 qd",
                    "108 qd",
                    "547 qd",
                    "560 qd",
                    "828 qd",
                    "364 qd",
                    "ielts 4 5",
                    "ielts 5 5",
                    "ielts 6 0",
                    "toeic 450",
                    "toeic 555",
                    "toeic 675",
                    "ielts academic",
                    "ielts general",
                ],
            ):
                score += 0.4
            if self._has_any(haystack, ["daa uit edu vn", "oep uit edu vn", "dao tao dai hoc", "van phong cac chuong trinh dac biet"]):
                score += 0.2

        if "registration" in topics:
            if self._has_any(haystack, ["dang ky hoc phan", "dkhp", "xac nhan dkhp", "hoc phan"]):
                score += 0.5
            if self._has_any(haystack, ["cong cu tu dong", "chiem cho", "dang ky thay", "nhan cho"]):
                score += 0.18
            if document_domain in {"daa.uit.edu.vn", "student.uit.edu.vn"} or self._has_any(haystack, ["daa uit edu vn", "student uit edu vn"]):
                score += 0.24

        if "tuition" in topics:
            if self._has_any(haystack, ["hoc phi", "thu hoc phi", "dong hoc phi", "gia han hoc phi", "mien giam hoc phi"]):
                score += 0.52
            if document_domain == "khtc.uit.edu.vn":
                score += 0.42
            elif document_domain in {"student.uit.edu.vn", "daa.uit.edu.vn", "oep.uit.edu.vn"} or self._has_any(haystack, ["daa uit edu vn", "student uit edu vn", "oep uit edu vn"]):
                score += 0.22

        if "scholarship" in topics:
            if self._has_any(haystack, ["hoc bong", "kkht", "khuyen khich hoc tap", "ngoai ngan sach", "xet hoc bong"]):
                score += 0.52
            if document_domain in {"ctsv.uit.edu.vn", "uit.edu.vn", "daa.uit.edu.vn"} or self._has_any(haystack, ["ctsv uit edu vn", "uit edu vn", "daa uit edu vn"]):
                score += 0.22

        if "graduation" in topics:
            if self._has_any(haystack, ["tot nghiep", "xet tot nghiep", "dieu kien tot nghiep", "ra truong"]):
                score += 0.5
            if document_domain in {"daa.uit.edu.vn", "student.uit.edu.vn", "khtc.uit.edu.vn"} or self._has_any(haystack, ["daa uit edu vn", "student uit edu vn", "quy trinh xu ly hoc vu"]):
                score += 0.24

        if "procedure" in topics:
            if self._has_any(haystack, ["giay xac nhan", "xac nhan sinh vien", "giay gioi thieu", "thu tuc", "bao luu", "tam ngung", "thoi hoc", "chuyen nganh", "song nganh"]):
                score += 0.48
            if document_domain in {"daa.uit.edu.vn", "student.uit.edu.vn"} or self._has_any(haystack, ["daa uit edu vn", "student uit edu vn", "portal sinh vien"]):
                score += 0.24

        if "schedule" in topics:
            if self._has_any(haystack, ["lich thi", "lich hoc", "thoi khoa bieu", "tkb", "giua ky", "cuoi ky", "dkhp", "dang ky hoc phan"]):
                score += 0.5
            if document_domain in {"student.uit.edu.vn", "daa.uit.edu.vn"} or self._has_any(haystack, ["student uit edu vn", "daa uit edu vn"]):
                score += 0.24

        if "annual_plan" in topics:
            if self._has_any(haystack, ["ke hoach dao tao nam hoc", "ke hoach nam", "khai giang", "tet am lich", "hk he", "ve he", "nghi he"]):
                score += 0.6
            if document_domain in {"daa.uit.edu.vn", "student.uit.edu.vn"}:
                score += 0.24

        if "academic_warning" in topics:
            if self._has_any(haystack, ["canh bao sinh vien", "canh bao hoc vu", "canh bao hoc tap", "xu ly hoc vu", "ket qua dang ky hoc phan", "ket qua hoc tap"]):
                score += 0.6
            if document_domain in {"student.uit.edu.vn", "daa.uit.edu.vn"}:
                score += 0.24

        if "curriculum" in topics:
            if self._has_any(haystack, ["chuong trinh dao tao", "ctdt", "ctdt khoa", "ke hoach hoc tap", "hoc mon nao"]):
                score += 0.5
            if self._has_any(haystack, ["student uit edu vn cqui ctdt khoa", "daa uit edu vn", "httt uit edu vn", "fce uit edu vn", "nc uit edu vn"]):
                score += 0.18

        if "special_program" in topics:
            if self._has_any(haystack, ["oep", "tai nang", "chat luong cao", "tien tien", "cttn", "ctclc", "cttt", "bcu", "uon"]):
                score += 0.52
            if self._has_any(haystack, ["oep uit edu vn", "van phong cac chuong trinh dac biet"]):
                score += 0.22

        if self._has_any(normalized_query, ["moi nhat", "hien tai", "nam nay", "2026", "2025", "2024"]) and document.updated_source_at:
            score += 0.08
            if str(document.updated_source_at.year) in normalized_query:
                score += 0.12
        if query_years:
            matched_years = query_years.intersection(self._query_years(haystack))
            score += 0.08 * len(matched_years)
            if not matched_years and self._query_years(haystack):
                score -= 0.04

        if "annual_plan" in topics and self._has_any(normalized_query, ["nghi he", "lich nghi", "ve he", "hoc ky he"]):
            if "2026" in query_years and self._has_any(haystack, ["2025 2026"]):
                score += 0.22
            if "2027" in query_years and self._has_any(haystack, ["2026 2027"]):
                score += 0.22
            if not query_years and self._has_any(haystack, ["2025 2026"]):
                score += 0.08

        return score

    def _candidate_excerpt(self, query: str, document: CollectedDocument, excerpt: str | None = None) -> str:
        source_text = " ".join((excerpt or document.summary or document.cleaned_content or "").split())
        if not source_text:
            return ""
        if len(source_text) <= 500:
            return source_text

        tokens = self._extract_tokens(query)
        query_years = self._query_years(query)
        sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", source_text) if segment.strip()]
        if not sentences:
            return source_text[:500]

        scored_sentences: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            normalized_sentence = self._normalize(sentence)
            token_hits = sum(1 for token in tokens if token in normalized_sentence)
            year_hits = sum(1 for year in query_years if year in normalized_sentence)
            score = (token_hits * 2.0) + (year_hits * 0.8)
            if index < 2:
                score += 0.1
            scored_sentences.append((score, index, sentence))

        if not any(item[0] > 0 for item in scored_sentences):
            return source_text[:500]

        scored_sentences.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        selected = sorted(scored_sentences[:2], key=lambda item: item[1])
        excerpt_text = " ".join(sentence for _, _, sentence in selected)
        return excerpt_text[:500]

    async def retrieve(self, db: Session, query: str, limit: int = 4) -> list[RetrievedContext]:
        candidates: dict[int, CandidateContext] = {}
        vector: list[float] = []

        try:
            embedding = await self.ollama.create_embedding(query)
            if isinstance(embedding, list):
                vector = embedding
        except Exception:
            vector = []

        scored_points = self.qdrant.search(vector, limit=max(limit * 3, limit)) if vector else []
        for item in scored_points:
            payload = item.payload or {}
            document_id = payload.get("document_id")
            if not document_id:
                continue
            document = db.query(CollectedDocument).filter(CollectedDocument.id == document_id).first()
            if not document:
                continue
            excerpt = self._candidate_excerpt(query, document, payload.get("content"))
            candidate = candidates.get(document_id)
            if candidate is None:
                candidate = CandidateContext(document=document, excerpt=excerpt)
                candidates[document_id] = candidate
            candidate.vector_score = max(candidate.vector_score, float(item.score or 0))
            if len(excerpt) > len(candidate.excerpt):
                candidate.excerpt = excerpt

        for document in (
            db.query(CollectedDocument)
            .order_by(CollectedDocument.updated_source_at.desc().nullslast(), CollectedDocument.id.desc())
            .limit(400)
            .all()
        ):
            candidate = candidates.get(document.id)
            if candidate is None:
                candidate = CandidateContext(document=document, excerpt=self._candidate_excerpt(query, document))
                candidates[document.id] = candidate

        ranked_contexts: list[RetrievedContext] = []
        for candidate in candidates.values():
            candidate.lexical_score = self._lexical_score(query, candidate.document, candidate.excerpt)
            candidate.source_score = self._source_hint_score(query, candidate.document)
            final_score = (candidate.vector_score * 0.3) + (candidate.lexical_score * 0.6) + candidate.source_score
            if candidate.vector_score == 0 and candidate.lexical_score == 0:
                continue
            ranked_contexts.append(
                RetrievedContext(
                    document=candidate.document,
                    excerpt=candidate.excerpt,
                    score=final_score,
                )
            )

        ranked_contexts.sort(key=lambda item: item.score, reverse=True)
        return ranked_contexts[:limit]
