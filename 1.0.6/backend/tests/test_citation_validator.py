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


def test_citation_validator_keeps_official_uit_url_without_citation() -> None:
    # Câu trả lời từ web_search (không có citation RAG) vẫn phải giữ nguồn UIT chính thức.
    answer = (
        "Hiệu trưởng là PGS.TS X.\n### Nguồn tham khảo\n"
        "- Trang Ban Giám hiệu: https://www.uit.edu.vn/bai-viet/ban-giam-hieu"
    )
    result = CitationValidator().clean_answer(answer, [])

    assert "https://www.uit.edu.vn/bai-viet/ban-giam-hieu" in result.answer
    assert result.removed_urls == []


def test_citation_validator_still_strips_non_uit_when_no_citation() -> None:
    answer = "Tham khảo https://student.uit.edu.vn/tin và https://random-fake.com/x"
    result = CitationValidator().clean_answer(answer, [])

    assert "https://student.uit.edu.vn/tin" in result.answer
    assert "https://random-fake.com/x" not in result.answer
