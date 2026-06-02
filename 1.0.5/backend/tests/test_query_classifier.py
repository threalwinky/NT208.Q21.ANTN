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
    assert result.category == "PLANNING"


def test_detects_announcement_query() -> None:
    result = analyze_query("Tuần này có thông báo mới nào từ CTSV không?")
    assert result.category == "ANNOUNCEMENT"


def test_detects_urgent_deadline_signal() -> None:
    result = analyze_query("Deadline này sát hạn rồi, hôm nay mình cần sắp lại việc gấp.")
    assert result.category == "PLANNING"
    assert result.is_urgent is True


def test_detects_self_harm_crisis_signal() -> None:
    for content in [
        "Mình không muốn sống nữa",
        "Mình muốn tự tử",
        "Mình muốn làm hại bản thân",
    ]:
        result = analyze_query(content)
        assert result.category == "WELLBEING"
        assert result.is_urgent is True
        assert result.risk_score >= 0.8


def test_non_crisis_wellbeing_message_stays_supportive() -> None:
    result = analyze_query("Mình thấy chán quá, không muốn học nữa")
    assert result.category == "WELLBEING"
    assert result.is_urgent is False
    assert result.risk_score < 0.8
