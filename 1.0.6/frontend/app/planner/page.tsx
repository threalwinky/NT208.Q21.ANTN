"use client";

import { AlertTriangle, CheckCircle, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import {
  addCourseToSemester,
  addSemester,
  completeTask,
  createStudyPlan,
  createTask,
  deleteStudyPlan,
  getClassSchedule,
  getCourses,
  getExamSchedule,
  getStudyPlans,
  getTasks,
  removeCourseFromSemester,
  removeSemester,
  validateStudyPlan,
  type Course,
  type StudyPlan,
  type StudyPlanValidationResult,
  type ValidationIssue,
} from "@/lib/api";
import { formatDateTime, formatDeadlineDistance } from "@/lib/format";

type PlannerTask = {
  id: number;
  title: string;
  task_type: string;
  priority: string;
  due_at?: string | null;
  status: string;
};

function toDateTimeLocalValue(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function sortTasksByDueDate(items: PlannerTask[]) {
  return [...items].sort((left, right) => {
    const leftTime = left.due_at ? new Date(left.due_at).getTime() : Number.POSITIVE_INFINITY;
    const rightTime = right.due_at ? new Date(right.due_at).getTime() : Number.POSITIVE_INFINITY;
    return leftTime - rightTime;
  });
}

type TabId = "schedule" | "tasks" | "roadmap";

export default function PlannerPage() {
  const [tab, setTab] = useState<TabId>("schedule");
  const [classSchedule, setClassSchedule] = useState<Array<Record<string, unknown>>>([]);
  const [examSchedule, setExamSchedule] = useState<Array<Record<string, unknown>>>([]);
  const [tasks, setTasks] = useState<PlannerTask[]>([]);
  const [title, setTitle] = useState("Nhắc đăng ký học phần");
  const [taskType, setTaskType] = useState("Học vụ");
  const [dueAt, setDueAt] = useState(() => toDateTimeLocalValue(new Date(Date.now() + 3 * 86400000)));

  // Roadmap state
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [activePlan, setActivePlan] = useState<StudyPlan | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [validation, setValidation] = useState<StudyPlanValidationResult | null>(null);
  const [courseSearch, setCourseSearch] = useState("");
  const [addingSemester, setAddingSemester] = useState(false);
  const [newSemesterLabel, setNewSemesterLabel] = useState("HK1 2025-2026");
  const [addingCourse, setAddingCourse] = useState<number | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [validating, setValidating] = useState(false);

  async function refreshSchedule() {
    const [classes, exams, tasksData] = await Promise.all([getClassSchedule(), getExamSchedule(), getTasks()]);
    setClassSchedule(classes);
    setExamSchedule(exams);
    setTasks(sortTasksByDueDate(tasksData as PlannerTask[]));
  }

  async function refreshPlans() {
    const data = await getStudyPlans();
    setPlans(data);
    if (data.length > 0 && !activePlan) {
      setActivePlan(data[0]);
    } else if (activePlan) {
      const fresh = data.find((p) => p.id === activePlan.id);
      setActivePlan(fresh ?? data[0] ?? null);
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      const [classes, exams, tasksData, planData, courseData] = await Promise.all([
        getClassSchedule(),
        getExamSchedule(),
        getTasks(),
        getStudyPlans(),
        getCourses(),
      ]);
      if (!mounted) return;
      setClassSchedule(classes);
      setExamSchedule(exams);
      setTasks(sortTasksByDueDate(tasksData as PlannerTask[]));
      setPlans(planData);
      if (planData.length > 0) setActivePlan(planData[0]);
      setCourses(courseData);
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  const filteredCourses = courseSearch.trim()
    ? courses.filter(
        (c) =>
          c.code.toLowerCase().includes(courseSearch.toLowerCase()) ||
          c.name.toLowerCase().includes(courseSearch.toLowerCase()),
      )
    : courses.slice(0, 30);

  async function handleCreatePlan() {
    const plan = await createStudyPlan({ name: "Kế hoạch học tập mới", total_required_credits: 130 });
    setActivePlan(plan);
    await refreshPlans();
  }

  async function handleAddSemester() {
    if (!activePlan || !newSemesterLabel.trim()) return;
    await addSemester(activePlan.id, { label: newSemesterLabel.trim(), max_credits: 24 });
    setAddingSemester(false);
    setNewSemesterLabel("HK1 2025-2026");
    await refreshPlans();
  }

  async function handleAddCourse(semId: number) {
    if (!activePlan || !selectedCourse) return;
    const course = courses.find((c) => c.code === selectedCourse);
    if (!course) return;
    await addCourseToSemester(activePlan.id, semId, {
      course_code: course.code,
      course_name: course.name,
      credits: course.credits,
      category: course.category,
    });
    setAddingCourse(null);
    setSelectedCourse("");
    await refreshPlans();
  }

  async function handleValidate() {
    if (!activePlan) return;
    setValidating(true);
    try {
      const result = await validateStudyPlan(activePlan.id);
      setValidation(result);
    } finally {
      setValidating(false);
    }
  }

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: "schedule", label: "Lịch học & thi" },
    { id: "tasks", label: "Việc cần làm" },
    { id: "roadmap", label: "Lộ trình học" },
  ];

  return (
    <AppShell
      pageTitle="Lịch và kế hoạch học"
      pageDescription="Quản lý lịch học, lịch thi, nhắc việc và lộ trình học tập theo từng học kỳ."
    >
      <div className="mb-5 flex gap-2 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`shrink-0 rounded-full px-5 py-2 text-sm font-medium transition ${
              tab === t.id
                ? "bg-[color:var(--accent)] text-white"
                : "border border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-secondary)] hover:bg-[color:var(--surface-hover)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Schedule tab ── */}
      {tab === "schedule" && (
        <div className="grid gap-5 xl:grid-cols-2 xl:gap-6">
          <AppCard title="Lịch học" subtitle="Block thời gian theo từng môn trong tuần.">
            <div className="space-y-3">
              {classSchedule.length === 0 ? (
                <p className="text-sm text-[color:var(--text-muted)]">Chưa có lịch học.</p>
              ) : (
                classSchedule.map((item) => (
                  <div key={String(item.id)} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="font-medium">{String(item.course_name)}</p>
                        <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                          {String(item.course_code)} • {String(item.room_name ?? "Chưa có phòng")}
                        </p>
                        <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                          GV: {String(item.lecturer_name ?? "Chưa cập nhật")}
                        </p>
                      </div>
                      <Badge tone="accent">
                        Thứ {String(item.weekday)} • Tiết {String(item.period_start)}-{String(item.period_end)}
                      </Badge>
                    </div>
                    <p className="mt-4 text-sm text-[color:var(--text-soft)]">Buổi kế tiếp: {formatDateTime(String(item.starts_at ?? ""))}</p>
                  </div>
                ))
              )}
            </div>
          </AppCard>

          <AppCard title="Lịch thi" subtitle="Các mốc thi cuối kỳ cần theo dõi.">
            <div className="space-y-3">
              {examSchedule.length === 0 ? (
                <p className="text-sm text-[color:var(--text-muted)]">Chưa có lịch thi.</p>
              ) : (
                examSchedule.map((item) => (
                  <div key={String(item.id)} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="font-medium">{String(item.course_name)}</p>
                        <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                          {String(item.course_code)} • {String(item.room_name ?? "Chưa có phòng")}
                        </p>
                      </div>
                      <Badge tone="warn">{String(item.exam_type ?? "Lịch thi")}</Badge>
                    </div>
                    <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(String(item.starts_at ?? ""))}</p>
                  </div>
                ))
              )}
            </div>
          </AppCard>
        </div>
      )}

      {/* ── Tasks tab ── */}
      {tab === "tasks" && (
        <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr] xl:gap-6">
          <AppCard title="Tạo việc mới" subtitle="Thêm nhanh một nhắc việc học vụ hoặc deadline cá nhân.">
            <div className="space-y-4">
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 outline-none"
                placeholder="Tên việc cần làm"
              />
              <select
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 outline-none"
              >
                <option>Học vụ</option>
                <option>Deadline</option>
                <option>Đồ án</option>
                <option>Học phí</option>
              </select>
              <label className="block space-y-2">
                <span className="text-sm font-medium text-[color:var(--text-primary)]">Deadline</span>
                <input
                  type="datetime-local"
                  value={dueAt}
                  onChange={(e) => setDueAt(e.target.value)}
                  className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 outline-none"
                />
              </label>
              <button
                type="button"
                onClick={async () => {
                  await createTask({ title, task_type: taskType, priority: "MEDIUM", due_at: dueAt ? new Date(dueAt).toISOString() : null });
                  await refreshSchedule();
                }}
                className="btn-primary inline-flex h-11 items-center gap-2 rounded-lg px-5 text-sm font-semibold transition"
              >
                <Plus className="h-4 w-4" />
                Thêm nhắc việc
              </button>
            </div>
          </AppCard>

          <AppCard title="Danh sách việc cần làm" subtitle="Tất cả việc đang mở, sắp xếp theo deadline.">
            <div className="space-y-3">
              {tasks.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5 text-sm text-[color:var(--text-muted)]">
                  Không còn việc nào đang mở.
                </div>
              ) : (
                tasks.map((item) => (
                  <div key={item.id} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">{item.title}</p>
                        <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.task_type}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge tone={item.due_at ? "accent" : "default"}>{formatDeadlineDistance(item.due_at)}</Badge>
                        <button
                          type="button"
                          onClick={async () => {
                            await completeTask(item.id);
                            await refreshSchedule();
                          }}
                          className="btn-secondary inline-flex h-11 items-center rounded-lg px-4 text-sm font-medium transition"
                        >
                          Đánh dấu xong
                        </button>
                      </div>
                    </div>
                    <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(item.due_at ?? "")}</p>
                  </div>
                ))
              )}
            </div>
          </AppCard>
        </div>
      )}

      {/* ── Roadmap tab ── */}
      {tab === "roadmap" && (
        <div className="space-y-5">
          {/* Plan selector */}
          <AppCard title="Kế hoạch học tập" subtitle="Lộ trình cá nhân theo từng học kỳ, có kiểm tra tiên quyết và tín chỉ.">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              {plans.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => { setActivePlan(p); setValidation(null); }}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                    activePlan?.id === p.id
                      ? "bg-[color:var(--accent)] text-white"
                      : "border border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-secondary)]"
                  }`}
                >
                  {p.name}
                </button>
              ))}
              <button
                type="button"
                onClick={handleCreatePlan}
                className="inline-flex items-center gap-1 rounded-full border border-dashed border-[color:var(--line)] px-4 py-2 text-sm text-[color:var(--text-muted)] hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] transition"
              >
                <Plus className="h-3.5 w-3.5" /> Kế hoạch mới
              </button>
              {activePlan && (
                <button
                  type="button"
                  onClick={async () => { await deleteStudyPlan(activePlan.id); setActivePlan(null); await refreshPlans(); }}
                  className="ml-auto inline-flex items-center gap-1 rounded-full px-3 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Xoá
                </button>
              )}
            </div>

            {activePlan && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-[color:var(--text-muted)]">
                  Yêu cầu tốt nghiệp: <b>{activePlan.total_required_credits} tín chỉ</b> •
                  Tối đa/HK: <b>{activePlan.max_credits_per_semester} tín chỉ</b>
                </span>
                <button
                  type="button"
                  onClick={handleValidate}
                  disabled={validating}
                  className="ml-auto btn-primary inline-flex h-9 items-center gap-2 rounded-md px-4 text-sm font-semibold transition disabled:opacity-60"
                >
                  {validating ? "Đang kiểm tra..." : "Kiểm tra kế hoạch"}
                </button>
              </div>
            )}
          </AppCard>

          {/* Validation result */}
          {validation && (
            <AppCard title="Kết quả kiểm tra" subtitle="">
              <div className={`mb-4 flex items-center gap-3 rounded-lg px-4 py-3 ${validation.valid ? "bg-green-50 dark:bg-green-900/20" : "bg-amber-50 dark:bg-amber-900/20"}`}>
                {validation.valid ? (
                  <CheckCircle className="h-5 w-5 shrink-0 text-green-600" />
                ) : (
                  <AlertTriangle className="h-5 w-5 shrink-0 text-amber-500" />
                )}
                <div>
                  <p className="font-medium text-sm">
                    {validation.valid ? "Kế hoạch hợp lệ" : "Có vấn đề cần xem xét"}
                  </p>
                  <p className="text-sm text-[color:var(--text-muted)]">
                    {validation.accumulated_unique_credits}/{activePlan?.total_required_credits ?? 130} tín chỉ —{" "}
                    {validation.graduation_progress_pct}% tiến độ tốt nghiệp
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                {validation.issues.map((issue: ValidationIssue, idx: number) => (
                  <div
                    key={idx}
                    className={`rounded-md px-4 py-3 text-sm ${
                      issue.severity === "error"
                        ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                        : "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
                    }`}
                  >
                    <span className="font-medium">[{issue.severity === "error" ? "Lỗi" : "Cảnh báo"}]</span>{" "}
                    {issue.message}
                  </div>
                ))}
              </div>
            </AppCard>
          )}

          {/* Semesters */}
          {activePlan && (
            <>
              {activePlan.semesters.map((sem) => (
                <AppCard
                  key={sem.id}
                  title={sem.label}
                  subtitle={`${sem.total_credits}/${sem.max_credits} tín chỉ`}
                >
                  <div className="space-y-2">
                    {sem.courses.length === 0 && (
                      <p className="text-sm text-[color:var(--text-muted)]">Chưa có môn nào.</p>
                    )}
                    {sem.courses.map((course) => (
                      <div key={course.id} className="flex items-center justify-between rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3">
                        <div>
                          <p className="text-sm font-medium">{course.course_code} — {course.course_name}</p>
                          <p className="text-xs text-[color:var(--text-muted)]">{course.credits} tín chỉ{course.category ? ` • ${course.category}` : ""}</p>
                        </div>
                        <button
                          type="button"
                          onClick={async () => {
                            await removeCourseFromSemester(activePlan.id, sem.id, course.course_code);
                            await refreshPlans();
                          }}
                          className="ml-3 p-1.5 text-[color:var(--text-muted)] hover:text-red-500 transition"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}

                    {addingCourse === sem.id ? (
                      <div className="mt-3 space-y-2">
                        <input
                          value={courseSearch}
                          onChange={(e) => setCourseSearch(e.target.value)}
                          className="w-full rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2 text-sm outline-none"
                          placeholder="Tìm môn học (mã hoặc tên)..."
                        />
                        <select
                          value={selectedCourse}
                          onChange={(e) => setSelectedCourse(e.target.value)}
                          className="w-full rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2 text-sm outline-none"
                          size={5}
                        >
                          <option value="">-- Chọn môn --</option>
                          {filteredCourses.map((c) => (
                            <option key={c.id} value={c.code}>
                              {c.code} — {c.name} ({c.credits} TC)
                            </option>
                          ))}
                        </select>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleAddCourse(sem.id)}
                            className="btn-primary h-9 rounded-md px-4 text-sm font-medium transition"
                          >
                            Thêm
                          </button>
                          <button
                            type="button"
                            onClick={() => { setAddingCourse(null); setSelectedCourse(""); setCourseSearch(""); }}
                            className="btn-secondary h-9 rounded-md px-4 text-sm transition"
                          >
                            Huỷ
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-3 flex gap-2">
                        <button
                          type="button"
                          onClick={() => setAddingCourse(sem.id)}
                          className="inline-flex items-center gap-1 rounded-md border border-dashed border-[color:var(--line)] px-3 py-2 text-sm text-[color:var(--text-muted)] hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] transition"
                        >
                          <Plus className="h-3.5 w-3.5" /> Thêm môn
                        </button>
                        <button
                          type="button"
                          onClick={async () => { await removeSemester(activePlan.id, sem.id); await refreshPlans(); }}
                          className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                        >
                          <Trash2 className="h-3.5 w-3.5" /> Xoá HK
                        </button>
                      </div>
                    )}
                  </div>
                </AppCard>
              ))}

              {/* Add semester */}
              {addingSemester ? (
                <AppCard title="Thêm học kỳ mới" subtitle="">
                  <div className="flex gap-3">
                    <input
                      value={newSemesterLabel}
                      onChange={(e) => setNewSemesterLabel(e.target.value)}
                      className="flex-1 rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2 text-sm outline-none"
                      placeholder="Ví dụ: HK1 2025-2026"
                    />
                    <button type="button" onClick={handleAddSemester} className="btn-primary h-10 rounded-md px-4 text-sm font-medium">Thêm</button>
                    <button type="button" onClick={() => setAddingSemester(false)} className="btn-secondary h-10 rounded-md px-4 text-sm">Huỷ</button>
                  </div>
                </AppCard>
              ) : (
                <button
                  type="button"
                  onClick={() => setAddingSemester(true)}
                  className="w-full rounded-lg border border-dashed border-[color:var(--line)] py-4 text-sm text-[color:var(--text-muted)] hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] transition"
                >
                  <Plus className="mr-1 inline h-4 w-4" />
                  Thêm học kỳ
                </button>
              )}
            </>
          )}

          {!activePlan && plans.length === 0 && (
            <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-8 text-center">
              <p className="text-[color:var(--text-muted)] text-sm">Chưa có kế hoạch học tập nào.</p>
              <button type="button" onClick={handleCreatePlan} className="btn-primary mt-4 h-10 rounded-md px-5 text-sm font-medium">
                Tạo kế hoạch đầu tiên
              </button>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
