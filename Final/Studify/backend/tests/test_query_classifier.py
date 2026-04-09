from app.services.query_classifier import analyze_query


def test_detects_wellbeing_signal() -> None:
    result = analyze_query("Mình đang buồn và hơi quá tải vì deadline")
    assert result.is_urgent is False
    assert result.category == "WELLBEING"


def test_detects_academic_query() -> None:
    result = analyze_query("Cho mình hỏi lịch thi và học phí kỳ này")
    assert result.is_urgent is False
    assert result.category == "ACADEMIC"


def test_detects_general_opening_message() -> None:
    result = analyze_query("Mình cần bạn giúp sắp lại tuần này")
    assert result.is_urgent is False
    assert result.category == "GENERAL"
