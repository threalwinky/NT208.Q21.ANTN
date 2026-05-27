from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.knowledge import (
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    DataSource,
    Department,
    DocumentChunk,
    SourceType,
)
from app.services.rag_service import RagService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_documents(db):
    source = DataSource(
        name="DAA",
        base_url="https://daa.uit.edu.vn",
        domain="daa.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    category = ContentCategory(code="ACADEMIC", display_name="Học vụ")
    department = Department(name="Phòng Đào tạo Đại học")
    db.add_all([source, category, department])
    db.flush()

    target = CollectedDocument(
        title="Hướng dẫn xin giấy xác nhận sinh viên trực tuyến",
        url="https://daa.uit.edu.vn/giay-xac-nhan",
        data_source_id=source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Quy trình xin giấy xác nhận sinh viên qua cổng DAA.",
        cleaned_content="Sinh viên truy cập cổng đào tạo DAA, mở biểu mẫu giấy xác nhận, điền thông tin và gửi yêu cầu trực tuyến.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    distractor = CollectedDocument(
        title="Thông báo thay đổi ngân hàng nhận học bổng",
        url="https://student.uit.edu.vn/hoc-bong-ngan-hang",
        data_source_id=source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Thông báo cập nhật ngân hàng nhận học bổng cho sinh viên.",
        cleaned_content="Sinh viên cập nhật thông tin tài khoản ngân hàng để nhận học bổng đúng hạn.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    db.add_all([target, distractor])
    db.flush()

    db.add_all(
        [
            DocumentChunk(
                document_id=target.id,
                chunk_index=0,
                content=target.cleaned_content or "",
                char_count=len(target.cleaned_content or ""),
            ),
            DocumentChunk(
                document_id=distractor.id,
                chunk_index=0,
                content=distractor.cleaned_content or "",
                char_count=len(distractor.cleaned_content or ""),
            ),
        ]
    )
    db.commit()
    return target, distractor


def seed_english_requirement_documents(db):
    source = DataSource(
        name="DAA English",
        base_url="https://daa.uit.edu.vn",
        domain="daa.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    category = ContentCategory(code="PROCEDURE", display_name="Thủ tục ngoại ngữ")
    department = Department(name="Bộ phận Ngoại ngữ")
    db.add_all([source, category, department])
    db.flush()

    target = CollectedDocument(
        title="Hướng dẫn sinh viên thực hiện các quy định về chuẩn quá trình và chuẩn đầu ra ngoại ngữ",
        url="https://daa.uit.edu.vn/content/huong-dan-sinh-vien-dai-hoc-he-chinh-quy-thuc-hien-cac-quy-dinh-ve-chuan-qua-trinh-va-chuan",
        data_source_id=source.id,
        category_id=category.id,
        department_id=department.id,
        summary="CTĐTr khóa 2024 trở về sau đạt TOEIC 4 kỹ năng Nghe-Đọc 450, Nói-Viết 185 hoặc tương đương. Bảng quy đổi nêu CTĐTr tương đương IELTS 4.5.",
        cleaned_content="Chuẩn đầu ra ngoại ngữ CTĐTr khóa 2024 trở về sau: TOEIC Nghe-Đọc 450, Nói-Viết 185 hoặc tương đương. Quy định ngoại ngữ công nhận IELTS 4.5 cho CTĐTr, IELTS 5.5 cho CTTN/CTCLC, IELTS 6.0 cho CTTT.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    distractor = CollectedDocument(
        title="Câu lạc bộ tiếng Anh sinh viên UIT",
        url="https://student.uit.edu.vn/clb-tieng-anh",
        data_source_id=source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Thông tin sinh hoạt câu lạc bộ tiếng Anh.",
        cleaned_content="Sinh viên trao đổi tiếng Anh, luyện giao tiếp và tham gia workshop IELTS.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    db.add_all([target, distractor])
    db.flush()

    db.add_all(
        [
            DocumentChunk(
                document_id=target.id,
                chunk_index=0,
                content=target.cleaned_content or "",
                char_count=len(target.cleaned_content or ""),
            ),
            DocumentChunk(
                document_id=distractor.id,
                chunk_index=0,
                content=distractor.cleaned_content or "",
                char_count=len(distractor.cleaned_content or ""),
            ),
        ]
    )
    db.commit()
    return target, distractor


def seed_annual_plan_documents(db):
    daa_source = DataSource(
        name="DAA",
        base_url="https://daa.uit.edu.vn",
        domain="daa.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    faculty_source = DataSource(
        name="Faculty",
        base_url="https://cs.uit.edu.vn",
        domain="cs.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    category = ContentCategory(code="ACADEMIC", display_name="Học vụ")
    department = Department(name="Phòng Đào tạo Đại học")
    db.add_all([daa_source, faculty_source, category, department])
    db.flush()

    target = CollectedDocument(
        title="Kế hoạch đào tạo năm học 2025-2026",
        url="https://daa.uit.edu.vn/sites/daa/files/uploads/pdtdh_bieu-do-ke-hoach-dao-tao-nam-hoc-2025-2026-ver-4-2.jpg",
        data_source_id=daa_source.id,
        category_id=category.id,
        department_id=department.id,
        summary="HK2 thi trong tháng 6/2026, học kỳ hè nằm khoảng giữa tháng 7/2026 đến giữa tháng 8/2026, không có kỳ nghỉ hè toàn trường cố định.",
        cleaned_content="Theo kế hoạch đào tạo năm học 2025-2026, giai đoạn thi học kỳ 2 nằm trong tháng 6/2026. Học kỳ hè của nhiều lớp chính quy bắt đầu khoảng giữa tháng 7/2026. Khoảng nghỉ thực tế của sinh viên nằm giữa cuối tháng 6 và đầu hoặc giữa tháng 7/2026 tùy học hè và GDQP&AN.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    distractor = CollectedDocument(
        title="Sinh hoạt mùa hè của câu lạc bộ khoa",
        url="https://cs.uit.edu.vn/sinh-hoat-mua-he",
        data_source_id=faculty_source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Thông báo hoạt động hè của câu lạc bộ sinh viên khoa.",
        cleaned_content="Câu lạc bộ tổ chức workshop mùa hè cho sinh viên khoa Khoa học Máy tính trong tháng 7.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    db.add_all([target, distractor])
    db.flush()
    db.add_all(
        [
            DocumentChunk(document_id=target.id, chunk_index=0, content=target.cleaned_content or "", char_count=len(target.cleaned_content or "")),
            DocumentChunk(document_id=distractor.id, chunk_index=0, content=distractor.cleaned_content or "", char_count=len(distractor.cleaned_content or "")),
        ]
    )
    db.commit()
    return target, distractor


def seed_tuition_documents(db):
    khtc_source = DataSource(
        name="KHTC",
        base_url="https://khtc.uit.edu.vn",
        domain="khtc.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    faculty_source = DataSource(
        name="Faculty",
        base_url="https://fit.uit.edu.vn",
        domain="fit.uit.edu.vn",
        source_type=SourceType.OFFICIAL,
        is_official_uit=True,
    )
    category = ContentCategory(code="TUITION", display_name="Học phí")
    department = Department(name="Phòng Kế hoạch - Tài chính")
    db.add_all([khtc_source, faculty_source, category, department])
    db.flush()

    target = CollectedDocument(
        title="[2025-2026] Thông báo thu học phí HK2, NH 2025-2026 trình độ ĐTĐH",
        url="https://khtc.uit.edu.vn/content/2025-2026-thong-bao-thu-hoc-phi-hk2-nh-2025-2026-trinh-do-dtdh",
        data_source_id=khtc_source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Học phí đợt 1 đến 22/02/2026, đợt 2 từ 16/03/2026 đến 17/05/2026, tra cứu tại student.uit.edu.vn/tracuu/hocphi.",
        cleaned_content="Phòng KHTC thông báo thu học phí HK2 năm học 2025-2026. Đợt 1 nộp đến 22/02/2026, đợt 2 từ 16/03/2026 đến 17/05/2026. Sinh viên tra cứu tại student.uit.edu.vn/tracuu/hocphi. Không nộp đúng hạn có thể bị xóa ĐKHP hoặc cấm thi.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    distractor = CollectedDocument(
        title="Thông tin học phí chương trình riêng của khoa",
        url="https://fit.uit.edu.vn/hoc-phi-chuong-trinh-rieng",
        data_source_id=faculty_source.id,
        category_id=category.id,
        department_id=department.id,
        summary="Thông tin tham khảo về học phí của một chương trình riêng.",
        cleaned_content="Một số nội dung giới thiệu học phí riêng của chương trình thuộc khoa, không phải thông báo thu học phí toàn trường.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
        is_academic_related=True,
    )
    db.add_all([target, distractor])
    db.flush()
    db.add_all(
        [
            DocumentChunk(document_id=target.id, chunk_index=0, content=target.cleaned_content or "", char_count=len(target.cleaned_content or "")),
            DocumentChunk(document_id=distractor.id, chunk_index=0, content=distractor.cleaned_content or "", char_count=len(distractor.cleaned_content or "")),
        ]
    )
    db.commit()
    return target, distractor


def test_hybrid_retrieval_prioritizes_keyword_match() -> None:
    db = make_session()
    try:
        target, distractor = seed_documents(db)
        service = RagService()

        async def fake_embedding(_: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        service.embedding_provider.embed = fake_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: [  # type: ignore[method-assign]
            SimpleNamespace(payload={"document_id": distractor.id, "content": distractor.cleaned_content}, score=0.95),
            SimpleNamespace(payload={"document_id": target.id, "content": target.cleaned_content}, score=0.35),
        ]

        contexts = asyncio.run(service.retrieve(db, "Cách xin giấy xác nhận sinh viên?", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
        assert contexts[0].score >= contexts[1].score
    finally:
        db.close()


def test_retrieve_falls_back_to_lexical_search_when_embedding_fails() -> None:
    db = make_session()
    try:
        target, _ = seed_documents(db)
        service = RagService()

        async def broken_embedding(_: str) -> list[float]:
            raise RuntimeError("ollama unavailable")

        service.embedding_provider.embed = broken_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: []  # type: ignore[method-assign]

        contexts = asyncio.run(service.retrieve(db, "Mình cần xin giấy xác nhận sinh viên", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
    finally:
        db.close()


def test_retrieve_prioritizes_official_english_requirement_documents() -> None:
    db = make_session()
    try:
        target, distractor = seed_english_requirement_documents(db)
        service = RagService()

        async def fake_embedding(_: str) -> list[float]:
            return [0.2, 0.1, 0.4]

        service.embedding_provider.embed = fake_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: [  # type: ignore[method-assign]
            SimpleNamespace(payload={"document_id": distractor.id, "content": distractor.cleaned_content}, score=0.96),
            SimpleNamespace(payload={"document_id": target.id, "content": target.cleaned_content}, score=0.31),
        ]

        contexts = asyncio.run(service.retrieve(db, "IELTS đầu ra tiếng Anh của trường là bao nhiêu?", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
        assert contexts[0].score >= contexts[1].score
    finally:
        db.close()


def test_retrieve_prioritizes_annual_plan_for_summer_break_queries() -> None:
    db = make_session()
    try:
        target, distractor = seed_annual_plan_documents(db)
        service = RagService()

        async def fake_embedding(_: str) -> list[float]:
            return [0.1, 0.3, 0.5]

        service.embedding_provider.embed = fake_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: [  # type: ignore[method-assign]
            SimpleNamespace(payload={"document_id": distractor.id, "content": distractor.cleaned_content}, score=0.94),
            SimpleNamespace(payload={"document_id": target.id, "content": target.cleaned_content}, score=0.25),
        ]

        contexts = asyncio.run(service.retrieve(db, "lịch nghỉ hè năm 2026", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
    finally:
        db.close()


def test_retrieve_prioritizes_khtc_for_generic_tuition_queries() -> None:
    db = make_session()
    try:
        target, distractor = seed_tuition_documents(db)
        service = RagService()

        async def fake_embedding(_: str) -> list[float]:
            return [0.6, 0.1, 0.2]

        service.embedding_provider.embed = fake_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: [  # type: ignore[method-assign]
            SimpleNamespace(payload={"document_id": distractor.id, "content": distractor.cleaned_content}, score=0.92),
            SimpleNamespace(payload={"document_id": target.id, "content": target.cleaned_content}, score=0.28),
        ]

        contexts = asyncio.run(service.retrieve(db, "thông tin học phí hk2 2025-2026", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
    finally:
        db.close()


def test_retrieve_prefers_matching_school_year_for_annual_plan_query() -> None:
    db = make_session()
    try:
        daa_source = DataSource(
            name="DAA",
            base_url="https://daa.uit.edu.vn",
            domain="daa.uit.edu.vn",
            source_type=SourceType.OFFICIAL,
            is_official_uit=True,
        )
        category = ContentCategory(code="ACADEMIC", display_name="Học vụ")
        department = Department(name="Phòng Đào tạo Đại học")
        db.add_all([daa_source, category, department])
        db.flush()

        target = CollectedDocument(
            title="Kế hoạch đào tạo năm học 2025-2026",
            url="https://daa.uit.edu.vn/sites/daa/files/uploads/pdtdh_bieu-do-ke-hoach-dao-tao-nam-hoc-2025-2026-ver-4-2.jpg",
            data_source_id=daa_source.id,
            category_id=category.id,
            department_id=department.id,
            summary="HK2 thi trong tháng 6/2026, sau đó có khoảng trống trước học kỳ hè khoảng đầu hoặc giữa tháng 7/2026.",
            cleaned_content="Kế hoạch đào tạo năm học 2025-2026 của DAA cho thấy học kỳ hè diễn ra sau giai đoạn thi HK2 tháng 6/2026.",
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
        )
        distractor = CollectedDocument(
            title="Kế hoạch đào tạo năm học 2026-2027",
            url="https://daa.uit.edu.vn/sites/daa/files/uploads/pdtdh_bieu_do_ke_hoach_dao_tao_nam_hoc_2026-2027-ver-5.jpg",
            data_source_id=daa_source.id,
            category_id=category.id,
            department_id=department.id,
            summary="Học kỳ hè nằm chủ yếu từ giữa tháng 7/2027 đến giữa tháng 8/2027.",
            cleaned_content="Kế hoạch đào tạo năm học 2026-2027 của DAA.",
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
        )
        db.add_all([target, distractor])
        db.flush()
        db.add_all(
            [
                DocumentChunk(document_id=target.id, chunk_index=0, content=target.cleaned_content or "", char_count=len(target.cleaned_content or "")),
                DocumentChunk(document_id=distractor.id, chunk_index=0, content=distractor.cleaned_content or "", char_count=len(distractor.cleaned_content or "")),
            ]
        )
        db.commit()

        service = RagService()

        async def fake_embedding(_: str) -> list[float]:
            return [0.2, 0.1, 0.6]

        service.embedding_provider.embed = fake_embedding  # type: ignore[method-assign]
        service.qdrant.search = lambda vector, limit=5: [  # type: ignore[method-assign]
            SimpleNamespace(payload={"document_id": distractor.id, "content": distractor.cleaned_content}, score=0.94),
            SimpleNamespace(payload={"document_id": target.id, "content": target.cleaned_content}, score=0.33),
        ]

        contexts = asyncio.run(service.retrieve(db, "lịch nghỉ hè năm 2026", limit=2))

        assert contexts
        assert contexts[0].document.id == target.id
    finally:
        db.close()
