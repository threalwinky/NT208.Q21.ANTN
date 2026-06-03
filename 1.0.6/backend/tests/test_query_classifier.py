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


def test_no_diacritic_crisis_typing_still_detected() -> None:
    # Người dùng gõ không dấu các cụm KHÔNG trùng homograph vẫn phải bắt được.
    for content in ["minh muon chet", "minh khong muon song nua"]:
        result = analyze_query(content)
        assert result.category == "WELLBEING"
        assert result.is_urgent is True
        assert result.risk_score >= 0.8


def test_emotional_messages_route_to_wellbeing_counseling() -> None:
    # Tin nhắn cảm xúc phải vào chế độ tư vấn tâm lý (WELLBEING), không lâm sàng/không crisis.
    for content in [
        "Dạo này mình thấy cô đơn quá",
        "Mình thấy mình bị trầm cảm hay sao ấy",
        "Cảm giác không ai hiểu mình cả",
        "Mình thấy lạc lõng và mất phương hướng",
    ]:
        result = analyze_query(content)
        assert result.category == "WELLBEING", content
        assert result.is_urgent is False, content
        assert result.risk_score < 0.8, content


def test_common_phrases_do_not_trigger_false_crisis() -> None:
    # Các câu bình thường trước đây bị báo động giả do bỏ dấu trùng homograph.
    safe_messages = [
        "Bạn cứ làm từ từ thôi, không cần vội",
        "Hướng dẫn từ từ giúp mình với",
        "Mình có hai bạn thân ở lớp",
        "Cho mình hỏi về tư vấn đời sống sinh viên",
    ]
    for content in safe_messages:
        result = analyze_query(content)
        assert result.risk_score < 0.8, content
        assert not (result.category == "WELLBEING" and result.is_urgent), content
