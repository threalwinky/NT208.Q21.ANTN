from __future__ import annotations

from app.services.query_rewriter import QueryRewriter, normalize_ascii


def test_normalize_ascii_handles_vietnamese_text() -> None:
    assert normalize_ascii("Đăng ký học phần") == "dang ky hoc phan"


def test_query_rewriter_expands_common_uit_abbreviations() -> None:
    rewritten = QueryRewriter().rewrite("dkhp tkb cntt hk này")

    assert "đăng ký học phần" in rewritten
    assert "thời khóa biểu" in rewritten
    assert "công nghệ thông tin" in rewritten


def test_query_rewriter_adds_topic_context_for_english_requirement() -> None:
    rewritten = QueryRewriter().rewrite("chuẩn tiếng Anh tốt nghiệp UIT")

    assert "TOEIC" in rewritten
    assert "điều kiện" in rewritten
