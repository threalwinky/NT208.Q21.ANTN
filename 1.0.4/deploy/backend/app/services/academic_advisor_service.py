from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.academic import Task, TaskStatus
from app.models.advisor import (
    AcademicRiskSnapshot,
    CourseCategory,
    CoursePrerequisite,
    CourseRecordStatus,
    DegreeCourse,
    DegreeProgram,
    ProgramCourseRequirement,
    PrerequisiteType,
    RiskLevel,
    StudentAcademicProfile,
    StudentCourseRecord,
)
from app.models.users import StudentProfile, User
from app.models.wellbeing import MoodJournal
from app.schemas.advisor import (
    AcademicRiskAlertOut,
    AdvisorCourseStatusOut,
    AdvisorIdentityOut,
    AdvisorOverviewOut,
    AuditCategoryProgressOut,
    DegreeAuditOut,
    GraphEdgeOut,
    GraphNodeOut,
    PlanCourseOut,
    SemesterPlanningOut,
    SemesterPlanOut,
)


@dataclass(slots=True)
class ComputedRisk:
    level: str
    score: int
    summary: str
    signals: list[str]
    recommendations: list[str]
    overdue_task_count: int
    failed_course_count: int
    current_gpa: float | None
    cumulative_gpa: float | None


STATUS_PRIORITY = {
    CourseRecordStatus.PASSED.value: 5,
    CourseRecordStatus.WAIVED.value: 5,
    CourseRecordStatus.IN_PROGRESS.value: 4,
    CourseRecordStatus.FAILED.value: 3,
    CourseRecordStatus.PLANNED.value: 2,
    CourseRecordStatus.WITHDRAWN.value: 1,
}

STATUS_LABELS = {
    CourseRecordStatus.PASSED.value: "Đã đạt",
    CourseRecordStatus.WAIVED.value: "Được miễn",
    CourseRecordStatus.IN_PROGRESS.value: "Đang học",
    CourseRecordStatus.FAILED.value: "Cần học lại",
    CourseRecordStatus.PLANNED.value: "Đã lên kế hoạch",
    CourseRecordStatus.WITHDRAWN.value: "Đã rút",
    "PENDING": "Chưa học",
}

CATEGORY_LABELS = {
    CourseCategory.CORE.value: "Cốt lõi",
    CourseCategory.FOUNDATION.value: "Nền tảng",
    CourseCategory.ELECTIVE.value: "Tự chọn",
    CourseCategory.THESIS.value: "Đồ án/Khóa luận",
    CourseCategory.ENGLISH.value: "Ngoại ngữ",
    CourseCategory.GENERAL.value: "Đại cương",
}


class AcademicAdvisorService:
    def _parse_cohort_year(self, student_profile: StudentProfile) -> int:
        cohort = student_profile.cohort or ""
        for token in cohort.replace("/", "-").split("-"):
            if token.isdigit() and len(token) == 4:
                return int(token)
        if student_profile.class_name and student_profile.class_name[-4:].isdigit():
            return int(student_profile.class_name[-4:])
        return datetime.now(timezone.utc).year

    def _cohort_reference(self, cohort_year: int, explicit_code: str | None = None) -> tuple[str, int | None]:
        cohort_index = max(1, cohort_year - 2005)
        label = explicit_code or f"K{cohort_index}"
        return f"{label} · tuyển {cohort_year}", cohort_year - 18 if cohort_year >= 2010 else None

    def _future_semester_codes(self) -> list[str]:
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month
        if month <= 5:
            return [f"Hè {year - 1}-{year}", f"HK1 {year}-{year + 1}"]
        if month <= 8:
            return [f"HK1 {year}-{year + 1}", f"HK2 {year}-{year + 1}"]
        return [f"HK2 {year}-{year + 1}", f"Hè {year}-{year + 1}"]

    def ensure_academic_profile(self, db: Session, user: User) -> StudentAcademicProfile:
        student_profile = user.student_profile
        if student_profile is None:
            raise ValueError("Người dùng chưa có hồ sơ sinh viên.")

        academic_profile = (
            db.query(StudentAcademicProfile)
            .options(joinedload(StudentAcademicProfile.program))
            .filter(StudentAcademicProfile.student_profile_id == student_profile.id)
            .first()
        )
        if academic_profile is not None:
            return academic_profile

        cohort_year = self._parse_cohort_year(student_profile)
        cohort_label, _ = self._cohort_reference(cohort_year)
        program = (
            db.query(DegreeProgram)
            .filter(
                DegreeProgram.major == student_profile.major,
                DegreeProgram.cohort_year == cohort_year,
            )
            .first()
        )
        if program is None:
            program = (
                db.query(DegreeProgram)
                .filter(DegreeProgram.major == student_profile.major)
                .order_by(DegreeProgram.cohort_year.desc())
                .first()
            )
        if program is None:
            raise ValueError("Chưa có CTĐT tương ứng cho sinh viên này.")

        academic_profile = StudentAcademicProfile(
            student_profile_id=student_profile.id,
            program_id=program.id,
            cohort_year=cohort_year,
            cohort_code=cohort_label.split(" · ", maxsplit=1)[0],
            expected_graduation_term=f"HK2 {cohort_year + 3}-{cohort_year + 4}",
            current_semester_index=1,
            target_credits_per_term=15,
        )
        db.add(academic_profile)
        db.commit()
        db.refresh(academic_profile)
        return academic_profile

    def _identity(self, student_profile: StudentProfile, academic_profile: StudentAcademicProfile) -> AdvisorIdentityOut:
        cohort_label, birth_year = self._cohort_reference(academic_profile.cohort_year, academic_profile.cohort_code)
        return AdvisorIdentityOut(
            student_name=student_profile.user.full_name,
            student_id=student_profile.student_id,
            faculty=student_profile.faculty,
            major=student_profile.major,
            class_name=student_profile.class_name,
            cohort_label=cohort_label,
            birth_year_hint=birth_year,
            expected_graduation_term=academic_profile.expected_graduation_term,
        )

    def _requirements(self, db: Session, academic_profile: StudentAcademicProfile) -> list[ProgramCourseRequirement]:
        return (
            db.query(ProgramCourseRequirement)
            .join(DegreeCourse, ProgramCourseRequirement.course_id == DegreeCourse.id)
            .options(
                joinedload(ProgramCourseRequirement.course)
                .joinedload(DegreeCourse.prerequisite_links)
                .joinedload(CoursePrerequisite.prerequisite_course)
            )
            .filter(ProgramCourseRequirement.program_id == academic_profile.program_id)
            .order_by(ProgramCourseRequirement.recommended_semester.asc(), DegreeCourse.code.asc())
            .all()
        )

    def _record_map(self, academic_profile: StudentAcademicProfile) -> dict[int, StudentCourseRecord]:
        record_map: dict[int, StudentCourseRecord] = {}
        records = sorted(
            academic_profile.course_records,
            key=lambda item: (
                STATUS_PRIORITY.get(item.status, 0),
                item.numeric_grade or -1,
                item.updated_at,
                item.id,
            ),
            reverse=True,
        )
        for record in records:
            record_map.setdefault(record.course_id, record)
        return record_map

    def _course_status(self, record: StudentCourseRecord | None) -> tuple[str, str]:
        if record is None:
            return "PENDING", STATUS_LABELS["PENDING"]
        return record.status, STATUS_LABELS.get(record.status, STATUS_LABELS["PENDING"])

    def _gpa_from_records(self, records: list[StudentCourseRecord], field_name: str) -> float | None:
        values = [
            record.numeric_grade
            for record in records
            if record.numeric_grade is not None and record.status in {CourseRecordStatus.PASSED.value, CourseRecordStatus.FAILED.value}
        ]
        if not values:
            return None
        average = sum(values) / len(values)
        return round(average, 2)

    def build_degree_audit(self, db: Session, user: User) -> DegreeAuditOut:
        academic_profile = self.ensure_academic_profile(db, user)
        student_profile = academic_profile.student_profile
        program = academic_profile.program
        requirements = self._requirements(db, academic_profile)
        record_map = self._record_map(academic_profile)

        total_required_credits = program.total_required_credits
        passed_credits = 0
        in_progress_credits = 0
        missing_core_courses: list[str] = []
        category_progress: dict[str, dict[str, int]] = defaultdict(lambda: {"required": 0, "passed": 0})
        course_rows: list[AdvisorCourseStatusOut] = []

        for requirement in requirements:
            course = requirement.course
            record = record_map.get(course.id)
            status, status_label = self._course_status(record)
            category_label = CATEGORY_LABELS.get(course.category, requirement.requirement_group)
            category_progress[category_label]["required"] += course.credits
            if status in {CourseRecordStatus.PASSED.value, CourseRecordStatus.WAIVED.value}:
                passed_credits += course.credits
                category_progress[category_label]["passed"] += course.credits
            elif status == CourseRecordStatus.IN_PROGRESS.value:
                in_progress_credits += course.credits
            elif requirement.is_required and course.category in {CourseCategory.CORE.value, CourseCategory.FOUNDATION.value, CourseCategory.THESIS.value}:
                missing_core_courses.append(course.code)

            course_rows.append(
                AdvisorCourseStatusOut(
                    course_id=course.id,
                    code=course.code,
                    name=course.name,
                    credits=course.credits,
                    category=category_label,
                    recommended_semester=requirement.recommended_semester,
                    requirement_group=requirement.requirement_group,
                    status=status,
                    status_label=status_label,
                    letter_grade=record.letter_grade if record else None,
                    semester_code=record.semester_code if record else None,
                    prerequisites=[link.prerequisite_course.code for link in course.prerequisite_links],
                )
            )

        remaining_credits = max(total_required_credits - passed_credits, 0)
        completion_percent = round((passed_credits / total_required_credits) * 100) if total_required_credits else 0

        if remaining_credits <= 15 and not missing_core_courses:
            milestone_summary = "Bạn đã vào chặng cuối. Nếu giữ nhịp hiện tại, khả năng chốt chuẩn tốt nghiệp khá tốt."
        elif missing_core_courses:
            milestone_summary = (
                f"Còn {len(missing_core_courses)} môn cốt lõi chưa hoàn tất. Nên ưu tiên các môn mở khóa trước để tránh dồn ở cuối chương trình."
            )
        else:
            milestone_summary = (
                f"Bạn đã hoàn thành khoảng {completion_percent}% CTĐT. Hãy giữ tải học kỳ tới quanh {academic_profile.target_credits_per_term} tín chỉ để tiến độ ổn định."
            )

        return DegreeAuditOut(
            identity=self._identity(student_profile, academic_profile),
            program_name=program.name,
            total_required_credits=total_required_credits,
            passed_credits=passed_credits,
            in_progress_credits=in_progress_credits,
            remaining_credits=remaining_credits,
            completion_percent=completion_percent,
            english_requirement=program.english_requirement,
            milestone_summary=milestone_summary,
            category_progress=[
                AuditCategoryProgressOut(
                    category=category,
                    required_credits=values["required"],
                    passed_credits=values["passed"],
                    remaining_credits=max(values["required"] - values["passed"], 0),
                )
                for category, values in category_progress.items()
            ],
            required_courses=course_rows,
            missing_core_courses=missing_core_courses,
        )

    def _build_graph_payload(
        self,
        requirements: list[ProgramCourseRequirement],
        record_map: dict[int, StudentCourseRecord],
        selected_plan_slots: dict[int, int],
    ) -> tuple[list[GraphNodeOut], list[GraphEdgeOut]]:
        nodes: list[GraphNodeOut] = []
        edges: list[GraphEdgeOut] = []
        for requirement in requirements:
            course = requirement.course
            status, _ = self._course_status(record_map.get(course.id))
            if course.id in selected_plan_slots:
                status = "PLANNED_NEXT"
            nodes.append(
                GraphNodeOut(
                    course_id=course.id,
                    code=course.code,
                    name=course.name,
                    credits=course.credits,
                    recommended_semester=requirement.recommended_semester,
                    category=CATEGORY_LABELS.get(course.category, requirement.requirement_group),
                    status=status,
                    plan_slot=selected_plan_slots.get(course.id),
                )
            )
            for prerequisite in course.prerequisite_links:
                edges.append(
                    GraphEdgeOut(
                        from_course_id=prerequisite.prerequisite_course_id,
                        to_course_id=course.id,
                        prerequisite_type=prerequisite.prerequisite_type,
                    )
                )
        return nodes, edges

    def _unlock_scores(self, requirements: list[ProgramCourseRequirement]) -> dict[int, int]:
        scores: dict[int, int] = defaultdict(int)
        for requirement in requirements:
            for prerequisite in requirement.course.prerequisite_links:
                scores[prerequisite.prerequisite_course_id] += 1
        return scores

    def _is_satisfied(
        self,
        course: DegreeCourse,
        passed_ids: set[int],
        planned_same_term: set[int] | None = None,
    ) -> bool:
        planned_same_term = planned_same_term or set()
        for prerequisite in course.prerequisite_links:
            if prerequisite.prerequisite_type == PrerequisiteType.RECOMMENDED.value:
                continue
            allowed_ids = passed_ids if prerequisite.prerequisite_type == PrerequisiteType.REQUIRED.value else passed_ids | planned_same_term
            if prerequisite.prerequisite_course_id not in allowed_ids:
                return False
        return True

    def _recommended_credit_load(self, risk_level: str, academic_profile: StudentAcademicProfile) -> int:
        if risk_level == RiskLevel.HIGH.value:
            return min(12, academic_profile.target_credits_per_term)
        if risk_level == RiskLevel.MEDIUM.value:
            return min(15, max(12, academic_profile.target_credits_per_term))
        return max(15, academic_profile.target_credits_per_term)

    def _build_risk(self, db: Session, academic_profile: StudentAcademicProfile, record_map: dict[int, StudentCourseRecord]) -> ComputedRisk:
        user = academic_profile.student_profile.user
        failed_records = [record for record in record_map.values() if record.status == CourseRecordStatus.FAILED.value]
        overdue_task_count = (
            db.query(Task)
            .filter(
                Task.user_id == user.id,
                Task.status != TaskStatus.DONE.value,
                Task.due_at.is_not(None),
                Task.due_at < datetime.now(timezone.utc),
            )
            .count()
        )
        latest_mood = (
            db.query(MoodJournal)
            .filter(MoodJournal.user_id == user.id, MoodJournal.is_soft_deleted.is_(False))
            .order_by(MoodJournal.created_at.desc())
            .first()
        )

        current_gpa = academic_profile.current_gpa or self._gpa_from_records(academic_profile.course_records, "current_gpa")
        cumulative_gpa = academic_profile.cumulative_gpa or self._gpa_from_records(academic_profile.course_records, "cumulative_gpa")
        score = 0
        signals: list[str] = []

        if current_gpa is not None and current_gpa < 2.2:
            score += 25
            signals.append(f"GPA học kỳ hiện tại đang ở mức {current_gpa:.2f}.")
        elif current_gpa is not None and current_gpa < 2.6:
            score += 14
            signals.append(f"GPA học kỳ hiện tại {current_gpa:.2f}, nên giữ tải học kỳ tới vừa phải.")

        if cumulative_gpa is not None and cumulative_gpa < 2.4:
            score += 16
            signals.append(f"GPA tích lũy {cumulative_gpa:.2f} đang khá sát vùng cảnh báo.")

        if failed_records:
            score += min(30, 10 * len(failed_records))
            signals.append(f"Có {len(failed_records)} môn cần học lại hoặc đang kéo lùi tiến độ.")

        if overdue_task_count:
            score += min(18, overdue_task_count * 6)
            signals.append(f"Có {overdue_task_count} việc đang quá hạn trong planner.")

        if latest_mood and latest_mood.energy_level <= 2:
            score += 16
            signals.append("Năng lượng gần đây xuống thấp, dễ hụt nhịp khi nhận tải học tập lớn.")
        elif latest_mood and latest_mood.energy_level == 3:
            score += 6
            signals.append("Năng lượng đang ở mức trung bình, nên tránh dồn môn mở khóa quá dày.")

        remaining_required = 0
        total_required = 0
        for requirement in self._requirements(db, academic_profile):
            if not requirement.is_required:
                continue
            total_required += 1
            record = record_map.get(requirement.course_id)
            if not record or record.status not in {CourseRecordStatus.PASSED.value, CourseRecordStatus.WAIVED.value}:
                remaining_required += 1
        if total_required:
            remaining_ratio = remaining_required / total_required
            if academic_profile.current_semester_index >= 5 and remaining_ratio > 0.5:
                score += 14
                signals.append("Tiến độ tích lũy đang chậm hơn mức thường thấy ở giai đoạn hiện tại.")

        score = max(0, min(score, 100))
        if score >= 65:
            level = RiskLevel.HIGH.value
            summary = "Bạn đang ở vùng rủi ro học tập cao. Nên giảm tải, chốt môn mở khóa và làm việc sớm với cố vấn học tập."
            recommendations = [
                "Giữ học kỳ tới quanh 12 tín chỉ và ưu tiên môn mở khóa hoặc môn đang nợ.",
                "Khóa ngay 2-3 việc quá hạn trong planner trong 48 giờ tới.",
                "Đặt lịch trao đổi với cố vấn học tập hoặc giáo vụ khoa để chốt lộ trình học lại.",
            ]
        elif score >= 35:
            level = RiskLevel.MEDIUM.value
            summary = "Bạn có vài dấu hiệu cần siết lại tiến độ. Nếu sắp tải môn hợp lý, bạn vẫn kéo nhịp học tập về quỹ đạo ổn."
            recommendations = [
                "Giữ tải học kỳ tới ở mức 14-15 tín chỉ, tránh gom quá nhiều môn nặng cùng lúc.",
                "Ưu tiên một môn mở khóa và một môn kéo GPA trước.",
                "Dọn các việc quá hạn trong tuần này để tránh trễ dây chuyền.",
            ]
        else:
            level = RiskLevel.LOW.value
            summary = "Rủi ro học tập hiện tại đang thấp. Bạn có thể giữ nhịp ổn định và tăng tốc vừa phải ở học kỳ tới."
            recommendations = [
                "Tiếp tục giữ block học đều để khóa dần các môn tiên quyết.",
                "Dành một phần tín chỉ cho môn mở rộng hoặc kỹ năng nếu lịch cho phép.",
                "Xem lại degree audit mỗi 2-3 tuần để bám tiến độ tốt nghiệp.",
            ]

        snapshot = (
            db.query(AcademicRiskSnapshot)
            .filter(AcademicRiskSnapshot.academic_profile_id == academic_profile.id)
            .order_by(AcademicRiskSnapshot.created_at.desc())
            .first()
        )
        if snapshot is None:
            snapshot = AcademicRiskSnapshot(
                academic_profile_id=academic_profile.id,
                risk_level=level,
                risk_score=score,
                summary=summary,
                signals_json=signals,
                recommendations_json=recommendations,
            )
            db.add(snapshot)
        else:
            snapshot.risk_level = level
            snapshot.risk_score = score
            snapshot.summary = summary
            snapshot.signals_json = signals
            snapshot.recommendations_json = recommendations
        db.commit()

        return ComputedRisk(
            level=level,
            score=score,
            summary=summary,
            signals=signals,
            recommendations=recommendations,
            overdue_task_count=overdue_task_count,
            failed_course_count=len(failed_records),
            current_gpa=current_gpa,
            cumulative_gpa=cumulative_gpa,
        )

    def build_semester_planning(self, db: Session, user: User) -> SemesterPlanningOut:
        academic_profile = self.ensure_academic_profile(db, user)
        student_profile = academic_profile.student_profile
        requirements = self._requirements(db, academic_profile)
        record_map = self._record_map(academic_profile)
        risk = self._build_risk(db, academic_profile, record_map)
        max_credits = self._recommended_credit_load(risk.level, academic_profile)
        unlock_scores = self._unlock_scores(requirements)

        passed_ids = {
            course_id
            for course_id, record in record_map.items()
            if record.status in {CourseRecordStatus.PASSED.value, CourseRecordStatus.WAIVED.value}
        }
        active_ids = {
            course_id
            for course_id, record in record_map.items()
            if record.status in {CourseRecordStatus.IN_PROGRESS.value, CourseRecordStatus.PLANNED.value}
        }

        remaining_requirements = [
            requirement
            for requirement in requirements
            if requirement.course_id not in passed_ids and requirement.course_id not in active_ids
        ]

        def requirement_sort_key(requirement: ProgramCourseRequirement) -> tuple[int, int, int, str]:
            record = record_map.get(requirement.course_id)
            is_failed = 0 if record and record.status == CourseRecordStatus.FAILED.value else 1
            is_optional = 1 if requirement.is_required else 2
            unlock_score = -unlock_scores.get(requirement.course_id, 0)
            return (is_failed, is_optional, requirement.recommended_semester, unlock_score, requirement.course.code)

        remaining_requirements = sorted(remaining_requirements, key=requirement_sort_key)
        semester_codes = self._future_semester_codes()

        selected_plan_slots: dict[int, int] = {}
        plans: list[SemesterPlanOut] = []
        available_passed_ids = set(passed_ids)

        for index, semester_code in enumerate(semester_codes, start=1):
            current_credits = 0
            selected_ids: set[int] = set()
            planned_courses: list[PlanCourseOut] = []

            for requirement in remaining_requirements:
                course = requirement.course
                if course.id in selected_plan_slots:
                    continue
                if current_credits + course.credits > max_credits:
                    continue
                if not self._is_satisfied(course, available_passed_ids, selected_ids):
                    continue

                reason_parts = []
                if record_map.get(course.id) and record_map[course.id].status == CourseRecordStatus.FAILED.value:
                    reason_parts.append("đã từng trượt nên cần kéo lại sớm")
                if unlock_scores.get(course.id):
                    reason_parts.append(f"mở khóa cho {unlock_scores[course.id]} môn sau")
                if requirement.recommended_semester < academic_profile.current_semester_index:
                    reason_parts.append("đang bị trễ so với nhịp CTĐT")
                if not reason_parts:
                    reason_parts.append("đúng nhịp đề xuất của CTĐT")

                planned_courses.append(
                    PlanCourseOut(
                        course_id=course.id,
                        code=course.code,
                        name=course.name,
                        credits=course.credits,
                        category=CATEGORY_LABELS.get(course.category, requirement.requirement_group),
                        planned_reason=", ".join(reason_parts),
                        prerequisite_codes=[link.prerequisite_course.code for link in course.prerequisite_links],
                    )
                )
                selected_ids.add(course.id)
                selected_plan_slots[course.id] = index
                current_credits += course.credits

            available_passed_ids |= selected_ids
            note = (
                "Ưu tiên nhẹ tải để giữ nhịp ổn định."
                if risk.level == RiskLevel.HIGH.value
                else "Cân bằng giữa môn mở khóa và môn kéo tiến độ tốt nghiệp."
            )
            plans.append(
                SemesterPlanOut(
                    title=f"Gợi ý học kỳ {index}",
                    semester_code=semester_code,
                    total_credits=current_credits,
                    max_credits=max_credits,
                    notes=note,
                    courses=planned_courses,
                )
            )

        blocked_codes = sorted(
            {
                prerequisite.prerequisite_course.code
                for requirement in remaining_requirements
                if requirement.course_id not in selected_plan_slots
                for prerequisite in requirement.course.prerequisite_links
                if prerequisite.prerequisite_course_id not in passed_ids
            }
        )
        nodes, edges = self._build_graph_payload(requirements, record_map, selected_plan_slots)

        return SemesterPlanningOut(
            identity=self._identity(student_profile, academic_profile),
            recommended_credit_load=max_credits,
            blocking_courses=blocked_codes,
            semesters=plans,
            graph_nodes=nodes,
            graph_edges=edges,
        )

    def build_academic_risk(self, db: Session, user: User) -> AcademicRiskAlertOut:
        academic_profile = self.ensure_academic_profile(db, user)
        student_profile = academic_profile.student_profile
        risk = self._build_risk(db, academic_profile, self._record_map(academic_profile))
        return AcademicRiskAlertOut(
            identity=self._identity(student_profile, academic_profile),
            risk_level=risk.level,
            risk_score=risk.score,
            summary=risk.summary,
            signals=risk.signals,
            recommendations=risk.recommendations,
            overdue_task_count=risk.overdue_task_count,
            failed_course_count=risk.failed_course_count,
            current_gpa=risk.current_gpa,
            cumulative_gpa=risk.cumulative_gpa,
        )

    def build_overview(self, db: Session, user: User) -> AdvisorOverviewOut:
        degree_audit = self.build_degree_audit(db, user)
        semester_planning = self.build_semester_planning(db, user)
        academic_risk = self.build_academic_risk(db, user)
        return AdvisorOverviewOut(
            degree_audit=degree_audit,
            semester_planning=semester_planning,
            academic_risk=academic_risk,
        )

    def dashboard_summary(self, db: Session, user: User) -> dict[str, int | str | None]:
        degree_audit = self.build_degree_audit(db, user)
        academic_risk = self.build_academic_risk(db, user)
        semester_planning = self.build_semester_planning(db, user)
        next_plan = semester_planning.semesters[0] if semester_planning.semesters else None
        return {
            "completionPercent": degree_audit.completion_percent,
            "remainingCredits": degree_audit.remaining_credits,
            "riskLevel": academic_risk.risk_level,
            "riskScore": academic_risk.risk_score,
            "nextSemesterCredits": next_plan.total_credits if next_plan else 0,
            "blockingCourses": len(semester_planning.blocking_courses),
        }
