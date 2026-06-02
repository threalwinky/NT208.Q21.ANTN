from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.advisor import (
    CourseCategory,
    CoursePrerequisite,
    CourseRecordStatus,
    DegreeCourse,
    DegreeProgram,
    ProgramCourseRequirement,
    PrerequisiteType,
    StudentAcademicProfile,
    StudentCourseRecord,
)
from app.models.users import StudentProfile


def upsert_course(
    db: Session,
    *,
    code: str,
    name: str,
    credits: int,
    category: str,
    department_name: str,
    description: str,
) -> DegreeCourse:
    course = db.query(DegreeCourse).filter(DegreeCourse.code == code).first()
    if course is None:
        course = DegreeCourse(code=code, name=name, credits=credits, category=category)
        db.add(course)
        db.flush()
    course.name = name
    course.credits = credits
    course.category = category
    course.department_name = department_name
    course.description = description
    return course


def upsert_program(
    db: Session,
    *,
    code: str,
    name: str,
    faculty: str,
    major: str,
    cohort_year: int,
    total_required_credits: int,
    english_requirement: str,
    notes: str,
) -> DegreeProgram:
    program = db.query(DegreeProgram).filter(DegreeProgram.code == code).first()
    if program is None:
        program = DegreeProgram(code=code, name=name, faculty=faculty, major=major, cohort_year=cohort_year, total_required_credits=total_required_credits)
        db.add(program)
        db.flush()
    program.name = name
    program.faculty = faculty
    program.major = major
    program.cohort_year = cohort_year
    program.total_required_credits = total_required_credits
    program.english_requirement = english_requirement
    program.notes = notes
    return program


def upsert_requirement(
    db: Session,
    *,
    program: DegreeProgram,
    course: DegreeCourse,
    recommended_semester: int,
    is_required: bool,
    requirement_group: str,
) -> None:
    requirement = (
        db.query(ProgramCourseRequirement)
        .filter(
            ProgramCourseRequirement.program_id == program.id,
            ProgramCourseRequirement.course_id == course.id,
        )
        .first()
    )
    if requirement is None:
        requirement = ProgramCourseRequirement(program_id=program.id, course_id=course.id)
        db.add(requirement)
    requirement.recommended_semester = recommended_semester
    requirement.is_required = is_required
    requirement.requirement_group = requirement_group


def upsert_prerequisite(
    db: Session,
    *,
    course: DegreeCourse,
    prerequisite_course: DegreeCourse,
    prerequisite_type: str = PrerequisiteType.REQUIRED.value,
) -> None:
    link = (
        db.query(CoursePrerequisite)
        .filter(
            CoursePrerequisite.course_id == course.id,
            CoursePrerequisite.prerequisite_course_id == prerequisite_course.id,
        )
        .first()
    )
    if link is None:
        link = CoursePrerequisite(course_id=course.id, prerequisite_course_id=prerequisite_course.id)
        db.add(link)
    link.prerequisite_type = prerequisite_type


def upsert_academic_profile(
    db: Session,
    *,
    student_profile: StudentProfile,
    program: DegreeProgram,
    cohort_year: int,
    cohort_code: str,
    current_semester_index: int,
    target_credits_per_term: int,
    cumulative_gpa: float,
    current_gpa: float,
    expected_graduation_term: str,
) -> StudentAcademicProfile:
    academic_profile = db.query(StudentAcademicProfile).filter(StudentAcademicProfile.student_profile_id == student_profile.id).first()
    if academic_profile is None:
        academic_profile = StudentAcademicProfile(student_profile_id=student_profile.id, program_id=program.id, cohort_year=cohort_year)
        db.add(academic_profile)
        db.flush()
    academic_profile.program_id = program.id
    academic_profile.cohort_year = cohort_year
    academic_profile.cohort_code = cohort_code
    academic_profile.current_semester_index = current_semester_index
    academic_profile.target_credits_per_term = target_credits_per_term
    academic_profile.cumulative_gpa = cumulative_gpa
    academic_profile.current_gpa = current_gpa
    academic_profile.expected_graduation_term = expected_graduation_term
    return academic_profile


def upsert_record(
    db: Session,
    *,
    academic_profile: StudentAcademicProfile,
    course: DegreeCourse,
    semester_code: str,
    status: str,
    letter_grade: str | None,
    numeric_grade: float | None,
    attempts: int = 1,
    notes: str | None = None,
) -> None:
    record = (
        db.query(StudentCourseRecord)
        .filter(
            StudentCourseRecord.academic_profile_id == academic_profile.id,
            StudentCourseRecord.course_id == course.id,
            StudentCourseRecord.semester_code == semester_code,
        )
        .first()
    )
    if record is None:
        record = StudentCourseRecord(academic_profile_id=academic_profile.id, course_id=course.id, semester_code=semester_code, status=status)
        db.add(record)
    record.status = status
    record.letter_grade = letter_grade
    record.numeric_grade = numeric_grade
    record.attempts = attempts
    record.notes = notes


def seed_advisor_demo_data(db: Session, student_profiles: dict[str, StudentProfile]) -> None:
    courses = {
        "MATH1123": upsert_course(
            db,
            code="MATH1123",
            name="Giải tích",
            credits=4,
            category=CourseCategory.FOUNDATION.value,
            department_name="Khoa Khoa học và Kỹ thuật Thông tin",
            description="Môn nền tảng toán cho các học phần chuyên ngành.",
        ),
        "IT001": upsert_course(
            db,
            code="IT001",
            name="Nhập môn lập trình",
            credits=4,
            category=CourseCategory.FOUNDATION.value,
            department_name="Khoa Công nghệ Phần mềm",
            description="Làm nền cho các học phần lập trình về sau.",
        ),
        "IT002": upsert_course(
            db,
            code="IT002",
            name="Lập trình hướng đối tượng",
            credits=4,
            category=CourseCategory.CORE.value,
            department_name="Khoa Công nghệ Phần mềm",
            description="Môn mở khóa cho phần lớn học phần chuyên ngành.",
        ),
        "IT003": upsert_course(
            db,
            code="IT003",
            name="Toán rời rạc cho CNTT",
            credits=3,
            category=CourseCategory.FOUNDATION.value,
            department_name="Khoa Khoa học Máy tính",
            description="Hỗ trợ tư duy thuật toán và cấu trúc rời rạc.",
        ),
        "EN001": upsert_course(
            db,
            code="EN001",
            name="Tiếng Anh học thuật 1",
            credits=3,
            category=CourseCategory.ENGLISH.value,
            department_name="Bộ môn Ngoại ngữ",
            description="Mốc tiếng Anh đầu tiên trong CTĐT.",
        ),
        "EN002": upsert_course(
            db,
            code="EN002",
            name="Tiếng Anh học thuật 2",
            credits=3,
            category=CourseCategory.ENGLISH.value,
            department_name="Bộ môn Ngoại ngữ",
            description="Mốc tiếng Anh nâng cao trước khi xét chuẩn đầu ra.",
        ),
        "CS221": upsert_course(
            db,
            code="CS221",
            name="Cấu trúc dữ liệu và giải thuật",
            credits=4,
            category=CourseCategory.CORE.value,
            department_name="Khoa Khoa học Máy tính",
            description="Môn xương sống cho nhánh thuật toán và AI.",
        ),
        "CS211": upsert_course(
            db,
            code="CS211",
            name="Kiến trúc máy tính",
            credits=3,
            category=CourseCategory.CORE.value,
            department_name="Khoa Kỹ thuật Máy tính",
            description="Kiến thức nền về hệ thống máy tính.",
        ),
        "CS331": upsert_course(
            db,
            code="CS331",
            name="Thiết kế và phân tích thuật toán",
            credits=4,
            category=CourseCategory.CORE.value,
            department_name="Khoa Khoa học Máy tính",
            description="Môn mở khóa cho đồ án và AI nâng cao.",
        ),
        "CS338": upsert_course(
            db,
            code="CS338",
            name="Cơ sở dữ liệu",
            credits=3,
            category=CourseCategory.CORE.value,
            department_name="Khoa Hệ thống Thông tin",
            description="Môn nền để làm đồ án và hệ thống thông tin.",
        ),
        "CS402": upsert_course(
            db,
            code="CS402",
            name="Nhập môn Học máy",
            credits=4,
            category=CourseCategory.ELECTIVE.value,
            department_name="Khoa Khoa học Máy tính",
            description="Học phần tự chọn chuyên sâu về AI.",
        ),
        "CS399": upsert_course(
            db,
            code="CS399",
            name="Phương pháp nghiên cứu khoa học",
            credits=2,
            category=CourseCategory.GENERAL.value,
            department_name="Khoa Khoa học Máy tính",
            description="Chuẩn bị cho hướng khóa luận, seminar, nghiên cứu.",
        ),
        "CS490": upsert_course(
            db,
            code="CS490",
            name="Khóa luận tốt nghiệp",
            credits=5,
            category=CourseCategory.THESIS.value,
            department_name="Khoa Khoa học Máy tính",
            description="Mốc hoàn tất cuối CTĐT ngành KHMT.",
        ),
        "NT101": upsert_course(
            db,
            code="NT101",
            name="Nhập môn mạng máy tính",
            credits=3,
            category=CourseCategory.CORE.value,
            department_name="Khoa Mạng máy tính và Truyền thông",
            description="Môn nhập môn cho nhánh hạ tầng mạng.",
        ),
        "NT201": upsert_course(
            db,
            code="NT201",
            name="Định tuyến và chuyển mạch",
            credits=4,
            category=CourseCategory.CORE.value,
            department_name="Khoa Mạng máy tính và Truyền thông",
            description="Môn mở khóa cho các học phần an toàn và enterprise.",
        ),
        "NT202": upsert_course(
            db,
            code="NT202",
            name="Quản trị hệ thống Linux",
            credits=3,
            category=CourseCategory.CORE.value,
            department_name="Khoa Mạng máy tính và Truyền thông",
            description="Môn nền cho cloud và hệ thống doanh nghiệp.",
        ),
        "NT301": upsert_course(
            db,
            code="NT301",
            name="An toàn mạng",
            credits=4,
            category=CourseCategory.CORE.value,
            department_name="Khoa Mạng máy tính và Truyền thông",
            description="Học phần chuyên sâu về bảo mật hạ tầng mạng.",
        ),
        "NT302": upsert_course(
            db,
            code="NT302",
            name="Điện toán đám mây cơ bản",
            credits=3,
            category=CourseCategory.ELECTIVE.value,
            department_name="Khoa Mạng máy tính và Truyền thông",
            description="Môn tự chọn về cloud và hạ tầng triển khai.",
        ),
        "NT401": upsert_course(
            db,
            code="NT401",
            name="Đồ án mạng doanh nghiệp",
            credits=5,
            category=CourseCategory.THESIS.value,
            department_name="Khoa Mạng máy tính và Truyền thông",
            description="Mốc capstone cho ngành MMT&TTDL.",
        ),
    }

    upsert_prerequisite(db, course=courses["IT002"], prerequisite_course=courses["IT001"])
    upsert_prerequisite(db, course=courses["EN002"], prerequisite_course=courses["EN001"])
    upsert_prerequisite(db, course=courses["CS221"], prerequisite_course=courses["IT002"])
    upsert_prerequisite(db, course=courses["CS221"], prerequisite_course=courses["IT003"])
    upsert_prerequisite(db, course=courses["CS331"], prerequisite_course=courses["CS221"])
    upsert_prerequisite(db, course=courses["CS338"], prerequisite_course=courses["IT002"])
    upsert_prerequisite(db, course=courses["CS402"], prerequisite_course=courses["CS331"])
    upsert_prerequisite(db, course=courses["CS490"], prerequisite_course=courses["CS331"])
    upsert_prerequisite(db, course=courses["CS490"], prerequisite_course=courses["CS338"])
    upsert_prerequisite(db, course=courses["NT101"], prerequisite_course=courses["IT001"])
    upsert_prerequisite(db, course=courses["NT201"], prerequisite_course=courses["NT101"])
    upsert_prerequisite(db, course=courses["NT202"], prerequisite_course=courses["IT002"])
    upsert_prerequisite(db, course=courses["NT301"], prerequisite_course=courses["NT201"])
    upsert_prerequisite(db, course=courses["NT302"], prerequisite_course=courses["NT202"])
    upsert_prerequisite(db, course=courses["NT401"], prerequisite_course=courses["NT301"])
    upsert_prerequisite(db, course=courses["NT401"], prerequisite_course=courses["NT202"])

    cs_program = upsert_program(
        db,
        code="UIT-KHMT-2022",
        name="Cử nhân Khoa học Máy tính",
        faculty="Khoa Khoa học Máy tính",
        major="Khoa học Máy tính",
        cohort_year=2022,
        total_required_credits=44,
        english_requirement="TOEIC 4 kỹ năng hoặc chứng chỉ tương đương theo quy định hiện hành của UIT.",
        notes="Bộ CTĐT demo để phục vụ degree audit và planning.",
    )
    security_program = upsert_program(
        db,
        code="UIT-ATTT-2022",
        name="Cử nhân An toàn thông tin",
        faculty="Khoa Mạng máy tính và Truyền thông",
        major="An toàn thông tin",
        cohort_year=2022,
        total_required_credits=43,
        english_requirement="TOEIC 4 kỹ năng hoặc chứng chỉ tương đương theo quy định hiện hành của UIT.",
        notes="Bộ CTĐT demo để phục vụ degree audit và planning.",
    )

    cs_requirements = [
        ("MATH1123", 1, True, "Nền tảng"),
        ("IT001", 1, True, "Nền tảng"),
        ("IT003", 1, True, "Nền tảng"),
        ("EN001", 2, True, "Ngoại ngữ"),
        ("IT002", 2, True, "Cốt lõi"),
        ("CS211", 3, True, "Cốt lõi"),
        ("CS221", 3, True, "Cốt lõi"),
        ("EN002", 4, True, "Ngoại ngữ"),
        ("CS338", 4, True, "Cốt lõi"),
        ("CS331", 5, True, "Cốt lõi"),
        ("CS399", 6, True, "Bổ trợ"),
        ("CS402", 6, False, "Tự chọn"),
        ("CS490", 8, True, "Tốt nghiệp"),
    ]
    security_requirements = [
        ("MATH1123", 1, True, "Nền tảng"),
        ("IT001", 1, True, "Nền tảng"),
        ("IT003", 1, True, "Nền tảng"),
        ("EN001", 2, True, "Ngoại ngữ"),
        ("IT002", 2, True, "Cốt lõi"),
        ("NT101", 2, True, "Cốt lõi"),
        ("EN002", 3, True, "Ngoại ngữ"),
        ("NT201", 4, True, "Cốt lõi"),
        ("NT202", 4, True, "Cốt lõi"),
        ("NT301", 5, True, "Cốt lõi"),
        ("NT302", 6, False, "Tự chọn"),
        ("NT401", 8, True, "Tốt nghiệp"),
    ]

    for course_code, semester, is_required, group in cs_requirements:
        upsert_requirement(
            db,
            program=cs_program,
            course=courses[course_code],
            recommended_semester=semester,
            is_required=is_required,
            requirement_group=group,
        )
    for course_code, semester, is_required, group in security_requirements:
        upsert_requirement(
            db,
            program=security_program,
            course=courses[course_code],
            recommended_semester=semester,
            is_required=is_required,
            requirement_group=group,
        )

    vu_profile = student_profiles.get("24522045")
    tu_profile = student_profiles.get("24520033")
    if vu_profile is None or tu_profile is None:
        return

    vu_academic = upsert_academic_profile(
        db,
        student_profile=vu_profile,
        program=security_program,
        cohort_year=2022,
        cohort_code="K17",
        current_semester_index=6,
        target_credits_per_term=12,
        cumulative_gpa=2.34,
        current_gpa=2.08,
        expected_graduation_term="HK1 2026-2027",
    )
    tu_academic = upsert_academic_profile(
        db,
        student_profile=tu_profile,
        program=cs_program,
        cohort_year=2022,
        cohort_code="K17",
        current_semester_index=6,
        target_credits_per_term=15,
        cumulative_gpa=3.03,
        current_gpa=2.78,
        expected_graduation_term="HK2 2025-2026",
    )

    tu_records = [
        ("MATH1123", "HK1 2022-2023", CourseRecordStatus.PASSED.value, "B+", 3.3, 1, None),
        ("IT001", "HK1 2022-2023", CourseRecordStatus.PASSED.value, "A", 3.8, 1, None),
        ("IT003", "HK1 2022-2023", CourseRecordStatus.PASSED.value, "A-", 3.6, 1, None),
        ("EN001", "HK2 2022-2023", CourseRecordStatus.PASSED.value, "B", 3.0, 1, None),
        ("IT002", "HK2 2022-2023", CourseRecordStatus.PASSED.value, "B+", 3.4, 1, None),
        ("CS211", "HK1 2023-2024", CourseRecordStatus.PASSED.value, "B", 3.0, 1, None),
        ("CS221", "HK1 2023-2024", CourseRecordStatus.PASSED.value, "B", 3.1, 1, None),
        ("CS338", "HK2 2023-2024", CourseRecordStatus.FAILED.value, "D", 1.8, 1, "Cần học lại để mở khóa luận."),
        ("CS331", "HK1 2024-2025", CourseRecordStatus.IN_PROGRESS.value, None, None, 1, "Đang là môn mở khóa quan trọng."),
        ("CS399", "HK2 2024-2025", CourseRecordStatus.PLANNED.value, None, None, 1, "Đã dự kiến đăng ký trong học kỳ tới."),
    ]
    vu_records = [
        ("MATH1123", "HK1 2022-2023", CourseRecordStatus.PASSED.value, "C+", 2.6, 1, None),
        ("IT001", "HK1 2022-2023", CourseRecordStatus.PASSED.value, "B", 3.0, 1, None),
        ("IT003", "HK1 2022-2023", CourseRecordStatus.PASSED.value, "C+", 2.5, 1, None),
        ("EN001", "HK2 2022-2023", CourseRecordStatus.PASSED.value, "C", 2.2, 1, None),
        ("IT002", "HK2 2022-2023", CourseRecordStatus.FAILED.value, "D", 1.7, 1, "Môn mở khóa cho nhiều học phần sau."),
        ("NT101", "HK2 2022-2023", CourseRecordStatus.PASSED.value, "C+", 2.4, 1, None),
        ("EN002", "HK1 2023-2024", CourseRecordStatus.PLANNED.value, None, None, 1, None),
        ("NT201", "HK1 2024-2025", CourseRecordStatus.IN_PROGRESS.value, None, None, 1, None),
        ("NT202", "HK2 2024-2025", CourseRecordStatus.PLANNED.value, None, None, 1, "Bị nghẽn do chưa chốt lại OOP."),
    ]

    for course_code, semester_code, status, letter_grade, numeric_grade, attempts, notes in vu_records:
        upsert_record(
            db,
            academic_profile=vu_academic,
            course=courses[course_code],
            semester_code=semester_code,
            status=status,
            letter_grade=letter_grade,
            numeric_grade=numeric_grade,
            attempts=attempts,
            notes=notes,
        )
    for course_code, semester_code, status, letter_grade, numeric_grade, attempts, notes in tu_records:
        upsert_record(
            db,
            academic_profile=tu_academic,
            course=courses[course_code],
            semester_code=semester_code,
            status=status,
            letter_grade=letter_grade,
            numeric_grade=numeric_grade,
            attempts=attempts,
            notes=notes,
        )
