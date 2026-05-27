from __future__ import annotations

from app.schemas.chat import CitationItem
from app.services.citation_validator import CitationValidator


def make_citation(url: str = "https://daa.uit.edu.vn/thong-bao") -> CitationItem:
    return CitationItem(
        document_id=1,
        title="Thông báo DAA",
        url=url,
        source_label="DAA",
        confidence="HIGH",
        excerpt="Nội dung trích dẫn",
        updated_at=None,
    )


def test_citation_validator_keeps_allowed_links() -> None:
    citation = make_citation()
    answer = "Xem [nguồn DAA](https://daa.uit.edu.vn/thong-bao) để kiểm tra."

    result = CitationValidator().clean_answer(answer, [citation])

    assert result.removed_urls == []
    assert "https://daa.uit.edu.vn/thong-bao" in result.answer


def test_citation_validator_removes_hallucinated_links() -> None:
    citation = make_citation()
    answer = "Nguồn đúng https://daa.uit.edu.vn/thong-bao và nguồn bịa https://evil.example/fake."

    result = CitationValidator().clean_answer(answer, [citation])

    assert "https://evil.example/fake" not in result.answer
    assert result.removed_urls == ["https://evil.example/fake"]
