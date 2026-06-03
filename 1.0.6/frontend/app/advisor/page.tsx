"use client";

import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  GraduationCap,
  ListChecks,
  Map,
  Route,
  ShieldAlert,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { PrerequisiteGraph } from "@/components/prerequisite-graph";
import { AppCard, Badge } from "@/components/ui";
import { getAdvisorOverview, getProfile, updateProfile, type AdvisorOverview, type Profile } from "@/lib/api";

type AdvisorTab = "tong-quan" | "tien-do" | "lo-trinh" | "rui-ro" | "ho-so";

const ADVISOR_TABS: Array<{
  id: AdvisorTab;
  label: string;
  description: string;
  icon: typeof GraduationCap;
}> = [
  { id: "tong-quan", label: "Tổng quan", description: "Hồ sơ và việc cần làm", icon: GraduationCap },
  { id: "tien-do", label: "Tiến độ", description: "Tín chỉ và môn ưu tiên", icon: ListChecks },
  { id: "lo-trinh", label: "Lộ trình", description: "Tiên quyết và kế hoạch", icon: Route },
  { id: "rui-ro", label: "Rủi ro", description: "Cảnh báo học tập", icon: ShieldAlert },
  { id: "ho-so", label: "Hồ sơ", description: "Thông tin cá nhân", icon: UserRound },
];

function statusTone(status: string): "default" | "accent" | "warn" | "danger" | "success" {
  if (status === "PASSED" || status === "WAIVED") return "success";
  if (status === "IN_PROGRESS") return "accent";
  if (status === "FAILED") return "danger";
  if (status === "PLANNED" || status === "PLANNED_NEXT") return "warn";
  return "default";
}

function riskTone(level?: string | null): "default" | "warn" | "danger" | "success" {
  if (level === "HIGH") return "danger";
  if (level === "MEDIUM") return "warn";
  if (level === "LOW") return "success";
  return "default";
}

function clampPercent(value?: number | null) {
  return Math.max(0, Math.min(100, Math.round(value ?? 0)));
}

function EmptyState({ children }: { children: string }) {
  return (
    <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-8 text-center text-sm text-[color:var(--text-muted)]">
      {children}
    </div>
  );
}

function MetricTile({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: typeof GraduationCap;
}) {
  return (
    <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-[color:var(--text-muted)]">{label}</p>
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-4 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)]">{value}</p>
      <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[color:var(--text-soft)]">{hint}</p>
    </div>
  );
}

function TabNavigation({ activeTab, onChange }: { activeTab: AdvisorTab; onChange: (tab: AdvisorTab) => void }) {
  return (
    <div
      role="tablist"
      aria-label="Nhóm nội dung học tập"
      className="grid gap-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-2 md:grid-cols-3 xl:grid-cols-5"
    >
      {ADVISOR_TABS.map((tab) => {
        const Icon = tab.icon;
        const selected = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            id={`advisor-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`advisor-panel-${tab.id}`}
            onClick={() => onChange(tab.id)}
            className={[
              "flex min-h-16 items-center gap-3 rounded-md border px-4 py-3 text-left text-sm transition",
              selected
                ? "border-[color:var(--accent)] bg-[color:var(--accent)] text-white shadow-sm"
                : "border-transparent bg-[color:var(--surface)] text-[color:var(--text-muted)] hover:border-[color:var(--line)] hover:text-[color:var(--text-primary)]",
            ].join(" ")}
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span className="min-w-0">
              <span className="block font-semibold">{tab.label}</span>
              <span className={`mt-0.5 hidden text-xs sm:block ${selected ? "text-white/75" : "text-[color:var(--text-soft)]"}`}>
                {tab.description}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function AdvisorPage() {
  const [activeTab, setActiveTab] = useState<AdvisorTab>("tong-quan");
  const [data, setData] = useState<AdvisorOverview | null>(null);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<Partial<Profile>>({});
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const payload = await getAdvisorOverview();
        if (mounted) {
          setData(payload);
        }
      } catch (caughtError) {
        if (mounted) {
          setError(caughtError instanceof Error ? caughtError.message : "Không tải được dữ liệu học tập.");
        }
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    getProfile().then((payload) => {
      if (!mounted) return;
      setProfile(payload);
      setForm(payload);
    });
    return () => {
      mounted = false;
    };
  }, []);

  async function save() {
    try {
      const updated = await updateProfile(form);
      setProfile(updated);
      setForm(updated);
      setSaveMsg("Đã lưu hồ sơ.");
    } catch (caughtError) {
      setSaveMsg(caughtError instanceof Error ? caughtError.message : "Không lưu được hồ sơ.");
    }
  }

  const priorityCourses = useMemo(
    () =>
      (data?.degree_audit.required_courses ?? [])
        .filter((course) => !["PASSED", "WAIVED"].includes(course.status))
        .slice(0, 8),
    [data],
  );

  const completionPercent = clampPercent(data?.degree_audit.completion_percent);
  const blockingCourses = data?.semester_planning.blocking_courses ?? [];
  const semesters = data?.semester_planning.semesters ?? [];
  const categoryProgress = data?.degree_audit.category_progress ?? [];
  const signals = data?.academic_risk.signals ?? [];
  const recommendations = data?.academic_risk.recommendations ?? [];

  return (
    <AppShell pageTitle="Học tập" pageDescription="Theo dõi tiến độ CTĐT, lộ trình môn học, cảnh báo học tập và hồ sơ sinh viên theo từng tab.">
      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <AppCard
          title="Hồ sơ học tập"
          subtitle="Studify dùng hồ sơ, CTĐT và kết quả hiện tại để đưa gợi ý."
          action={<Badge tone="accent">{data?.degree_audit.identity.cohort_label ?? "Đang đồng bộ"}</Badge>}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Sinh viên</p>
              <p className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{data?.degree_audit.identity.student_name ?? "..."}</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                MSSV {data?.degree_audit.identity.student_id ?? "..."} • {data?.degree_audit.identity.class_name ?? "..."}
              </p>
            </div>
            <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Ngành học</p>
              <p className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{data?.degree_audit.program_name ?? "..."}</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                {data?.degree_audit.identity.faculty ?? "..."} • Dự kiến {data?.degree_audit.identity.expected_graduation_term ?? "..."}
              </p>
            </div>
          </div>
        </AppCard>

        <AppCard
          title="Cảnh báo nhanh"
          subtitle="Đọc từ GPA, môn nợ, task quá hạn và nhịp học gần đây."
          action={<Badge tone={riskTone(data?.academic_risk.risk_level)}>{data?.academic_risk.risk_level ?? "LOW"}</Badge>}
        >
          <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
            <p className="text-sm text-[color:var(--text-muted)]">Tóm tắt</p>
            <p className="mt-2 text-base font-medium leading-6 text-[color:var(--text-primary)]">
              {data?.academic_risk.summary ?? "Đang phân tích dữ liệu học tập..."}
            </p>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Risk score</p>
              <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{data?.academic_risk.risk_score ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Môn nợ</p>
              <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{data?.academic_risk.failed_course_count ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Quá hạn</p>
              <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{data?.academic_risk.overdue_task_count ?? 0}</p>
            </div>
          </div>
        </AppCard>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Tiến độ CTĐT" value={`${completionPercent}%`} hint="Degree audit" icon={GraduationCap} />
        <MetricTile label="Tín chỉ còn lại" value={`${data?.degree_audit.remaining_credits ?? 0}`} hint="Cần hoàn thành" icon={ListChecks} />
        <MetricTile label="Tải kỳ gợi ý" value={`${data?.semester_planning.recommended_credit_load ?? 0} TC`} hint="Theo risk score" icon={Clock3} />
        <MetricTile label="Môn đang chặn" value={`${blockingCourses.length}`} hint="Tiên quyết" icon={Map} />
      </section>

      <TabNavigation activeTab={activeTab} onChange={setActiveTab} />

      <div id={`advisor-panel-${activeTab}`} role="tabpanel" aria-labelledby={`advisor-tab-${activeTab}`} className="space-y-4">
        {activeTab === "tong-quan" ? (
          <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
            <AppCard
              title="Việc học nên ưu tiên"
              subtitle="Các môn chưa khép được sắp trước để giảm rủi ro và mở khóa lộ trình."
              action={
                <button
                  type="button"
                  onClick={() => setActiveTab("tien-do")}
                  className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]"
                >
                  Xem tiến độ
                </button>
              }
            >
              <div className="space-y-3">
                {priorityCourses.length === 0 ? (
                  <EmptyState>Chưa có môn ưu tiên cần hiển thị.</EmptyState>
                ) : (
                  priorityCourses.slice(0, 4).map((course) => (
                    <div key={course.course_id} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="font-semibold text-[color:var(--text-primary)]">
                            {course.code} • {course.name}
                          </p>
                          <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                            {course.category} • Gợi ý từ học kỳ {course.recommended_semester}
                          </p>
                        </div>
                        <Badge tone={statusTone(course.status)}>{course.status_label}</Badge>
                      </div>
                      {course.prerequisites.length ? (
                        <p className="mt-3 text-sm text-[color:var(--text-soft)]">Tiên quyết: {course.prerequisites.join(", ")}</p>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </AppCard>

            <div className="space-y-4">
              <AppCard
                title="Tiến độ hiện tại"
                subtitle="Tín chỉ đã qua so với tổng yêu cầu CTĐT."
                action={<Badge tone="accent">{data?.degree_audit.passed_credits ?? 0}/{data?.degree_audit.total_required_credits ?? 0} TC</Badge>}
              >
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="text-sm text-[color:var(--text-muted)]">Hoàn thành</p>
                    <p className="mt-2 text-4xl font-semibold tracking-tight text-[color:var(--text-primary)]">{completionPercent}%</p>
                  </div>
                  <p className="max-w-[18rem] text-right text-sm leading-6 text-[color:var(--text-muted)]">{data?.degree_audit.milestone_summary ?? "Đang đồng bộ."}</p>
                </div>
                <div className="mt-4 h-3 overflow-hidden rounded-full bg-[color:var(--surface-soft)]">
                  <div className="h-full rounded-full bg-[color:var(--accent)]" style={{ width: `${completionPercent}%` }} />
                </div>
              </AppCard>

              <AppCard title="Lối tắt" subtitle="Các màn hình thường cần khi xử lý học tập.">
                <div className="grid gap-3">
                  <Link href="/gpa" className="group rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[color:var(--text-primary)]">Tính GPA mục tiêu</p>
                        <p className="mt-1 text-sm text-[color:var(--text-muted)]">Mô phỏng điểm kỳ này trước khi đăng ký tải học.</p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-[color:var(--text-soft)] transition group-hover:translate-x-1 group-hover:text-[color:var(--accent)]" />
                    </div>
                  </Link>
                  <Link href="/planner" className="group rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[color:var(--text-primary)]">Sắp lịch học tuần này</p>
                        <p className="mt-1 text-sm text-[color:var(--text-muted)]">Đưa môn ưu tiên và deadline vào block học ngắn.</p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-[color:var(--text-soft)] transition group-hover:translate-x-1 group-hover:text-[color:var(--accent)]" />
                    </div>
                  </Link>
                </div>
              </AppCard>
            </div>
          </div>
        ) : null}

        {activeTab === "tien-do" ? (
          <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <AppCard
              title="Nhóm tín chỉ"
              subtitle="Theo dõi từng nhóm yêu cầu trong chương trình đào tạo."
              action={<Badge tone="accent">{data?.degree_audit.passed_credits ?? 0}/{data?.degree_audit.total_required_credits ?? 0} TC</Badge>}
            >
              <div className="space-y-4">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-center justify-between gap-4 text-sm">
                    <span className="text-[color:var(--text-muted)]">Tiến độ hoàn thành</span>
                    <span className="font-semibold text-[color:var(--text-primary)]">{completionPercent}%</span>
                  </div>
                  <div className="mt-3 h-3 rounded-full bg-[color:var(--surface-strong)]">
                    <div className="h-3 rounded-full bg-[color:var(--accent)]" style={{ width: `${completionPercent}%` }} />
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {categoryProgress.length === 0 ? (
                    <div className="sm:col-span-2">
                      <EmptyState>Chưa có dữ liệu nhóm tín chỉ.</EmptyState>
                    </div>
                  ) : (
                    categoryProgress.map((item) => (
                      <div key={item.category} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                        <p className="text-sm font-semibold text-[color:var(--text-primary)]">{item.category}</p>
                        <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                          {item.passed_credits}/{item.required_credits} tín chỉ
                        </p>
                        <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[color:var(--text-soft)]">Còn {item.remaining_credits} TC</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </AppCard>

            <AppCard title="Môn ưu tiên tiếp theo" subtitle="Các môn chưa đạt, đang học hoặc nên đưa vào kế hoạch kỳ tới.">
              <div className="space-y-3">
                {priorityCourses.length === 0 ? (
                  <EmptyState>Chưa có môn ưu tiên cần hiển thị.</EmptyState>
                ) : (
                  priorityCourses.map((course) => (
                    <div key={course.course_id} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="font-semibold text-[color:var(--text-primary)]">
                            {course.code} • {course.name}
                          </p>
                          <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                            {course.category} • {course.credits} TC • {course.requirement_group}
                          </p>
                        </div>
                        <Badge tone={statusTone(course.status)}>{course.status_label}</Badge>
                      </div>
                      {course.prerequisites.length ? (
                        <p className="mt-3 text-sm text-[color:var(--text-soft)]">Tiên quyết: {course.prerequisites.join(", ")}</p>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </AppCard>
          </div>
        ) : null}

        {activeTab === "lo-trinh" ? (
          <div className="space-y-4">
            <AppCard
              title="Sơ đồ tiên quyết"
              subtitle="Mỗi mũi tên là một ràng buộc tiên quyết; màu trạng thái cho biết nên chốt môn nào trước."
              action={<Badge tone={blockingCourses.length ? "warn" : "success"}>{blockingCourses.length ? `${blockingCourses.length} môn đang chặn` : "Luồng học đang thông"}</Badge>}
            >
              <div className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2 text-xs text-[color:var(--text-muted)]">
                    <GraduationCap className="h-4 w-4 text-[color:var(--accent)]" />
                    Tiến độ CTĐT bám theo bộ dữ liệu học tập đã seed
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2 text-xs text-[color:var(--text-muted)]">
                    <Route className="h-4 w-4 text-[color:var(--accent)]" />
                    Ưu tiên môn mở khóa và môn đang nợ
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2 text-xs text-[color:var(--text-muted)]">
                    <Clock3 className="h-4 w-4 text-[color:var(--accent)]" />
                    {data?.degree_audit.english_requirement ?? "Chuẩn ngoại ngữ đang được theo dõi riêng"}
                  </div>
                </div>
                <PrerequisiteGraph nodes={data?.semester_planning.graph_nodes ?? []} edges={data?.semester_planning.graph_edges ?? []} />
                {blockingCourses.length ? (
                  <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-sm leading-6 text-[color:var(--text-muted)]">
                    Các môn đang chặn luồng hiện tại: {blockingCourses.join(", ")}.
                  </div>
                ) : null}
              </div>
            </AppCard>

            <AppCard
              title="Kế hoạch học kỳ"
              subtitle="Studify sắp 2 học kỳ tới theo môn mở khóa, môn nợ và tải tín chỉ phù hợp."
              action={<Badge tone="accent">{data?.semester_planning.recommended_credit_load ?? 0} TC/kỳ</Badge>}
            >
              <div className="grid gap-4 xl:grid-cols-2">
                {semesters.length === 0 ? (
                  <div className="xl:col-span-2">
                    <EmptyState>Chưa có kế hoạch học kỳ.</EmptyState>
                  </div>
                ) : (
                  semesters.map((semester) => (
                    <div key={semester.semester_code} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-[color:var(--text-primary)]">{semester.title}</p>
                          <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                            {semester.semester_code} • {semester.total_credits}/{semester.max_credits} tín chỉ
                          </p>
                        </div>
                        <Badge tone="accent">{semester.total_credits} TC</Badge>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{semester.notes}</p>
                      <div className="mt-4 space-y-3">
                        {semester.courses.map((course) => (
                          <div key={course.course_id} className="rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] p-4">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="font-semibold text-[color:var(--text-primary)]">
                                {course.code} • {course.name}
                              </p>
                              <Badge tone="default">{course.credits} TC</Badge>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{course.planned_reason}</p>
                            {course.prerequisite_codes.length ? (
                              <p className="mt-2 text-sm text-[color:var(--text-soft)]">Tiên quyết: {course.prerequisite_codes.join(", ")}</p>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </AppCard>
          </div>
        ) : null}

        {activeTab === "rui-ro" ? (
          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <AppCard
              title="Điểm rủi ro học tập"
              subtitle="Tín hiệu tổng hợp từ GPA, môn nợ và các việc quá hạn."
              action={<Badge tone={riskTone(data?.academic_risk.risk_level)}>{data?.academic_risk.risk_level ?? "LOW"}</Badge>}
            >
              <div className="space-y-4">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm text-[color:var(--text-muted)]">Risk score</p>
                  <p className="mt-2 text-5xl font-semibold tracking-tight text-[color:var(--text-primary)]">{data?.academic_risk.risk_score ?? 0}</p>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{data?.academic_risk.summary ?? "Đang phân tích dữ liệu học tập."}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <p className="text-sm text-[color:var(--text-muted)]">GPA học kỳ</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{data?.academic_risk.current_gpa ?? "--"}</p>
                  </div>
                  <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <p className="text-sm text-[color:var(--text-muted)]">GPA tích lũy</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{data?.academic_risk.cumulative_gpa ?? "--"}</p>
                  </div>
                </div>
              </div>
            </AppCard>

            <AppCard title="Tín hiệu và bước xử lý" subtitle="Các lý do kéo risk score lên và hành động nên làm ngay.">
              <div className="grid gap-4">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                    <AlertTriangle className="h-4 w-4 text-[color:var(--accent)]" />
                    Tín hiệu đang theo dõi
                  </div>
                  <div className="mt-3 space-y-2">
                    {signals.length === 0 ? (
                      <EmptyState>Chưa có tín hiệu rủi ro.</EmptyState>
                    ) : (
                      signals.map((signal) => (
                        <div key={signal} className="rounded-md bg-[color:var(--surface)] px-3 py-3 text-sm leading-6 text-[color:var(--text-primary)]">
                          {signal}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                    <CheckCircle2 className="h-4 w-4 text-[color:var(--accent)]" />
                    Bước nên làm ngay
                  </div>
                  <div className="mt-3 space-y-2">
                    {recommendations.length === 0 ? (
                      <EmptyState>Chưa có khuyến nghị cụ thể.</EmptyState>
                    ) : (
                      recommendations.map((item) => (
                        <div key={item} className="rounded-md bg-[color:var(--surface)] px-3 py-3 text-sm leading-6 text-[color:var(--text-primary)]">
                          {item}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </AppCard>
          </div>
        ) : null}

        {activeTab === "ho-so" ? (
          <div className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
            <AppCard title="Tóm tắt hồ sơ" subtitle="Thông tin này dùng để cá nhân hóa cố vấn học tập trong app.">
              <div className="space-y-4">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm text-[color:var(--text-muted)]">Tài khoản</p>
                  <p className="mt-2 text-xl font-semibold text-[color:var(--text-primary)]">{profile?.full_name ?? "Đang tải..."}</p>
                  <p className="mt-1 text-sm text-[color:var(--text-soft)]">@{profile?.username ?? "studify"}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="accent">{profile?.role ?? "STUDENT"}</Badge>
                  <Badge tone="success">{profile?.student_id ? `MSSV ${profile.student_id}` : "Chưa có MSSV"}</Badge>
                </div>
                {saveMsg ? (
                  <p className="rounded-lg bg-[color:var(--accent-soft)] px-4 py-3 text-sm text-[color:var(--accent)]">{saveMsg}</p>
                ) : null}
              </div>
            </AppCard>

            <AppCard title="Cập nhật hồ sơ" subtitle="Các trường học vụ có thể chỉnh để demo đúng ngành/lớp của sinh viên.">
              <div className="grid gap-3 md:grid-cols-2">
                {(
                  [
                    ["full_name", "Họ tên"],
                    ["email", "Email"],
                    ["student_id", "MSSV"],
                    ["faculty", "Khoa"],
                    ["major", "Ngành"],
                    ["class_name", "Lớp"],
                    ["cohort", "Khóa"],
                    ["advisor_name", "Cố vấn học tập"],
                  ] as Array<[keyof Profile, string]>
                ).map(([key, label]) => (
                  <label key={key} className="block">
                    <span className="text-sm text-[color:var(--text-muted)]">{label}</span>
                    <input
                      value={String(form[key] ?? "")}
                      onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
                      className="mt-2 w-full rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2.5 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-[color:var(--accent)]"
                    />
                  </label>
                ))}
              </div>
              <button type="button" onClick={save} className="btn-primary mt-5 rounded-md px-5 py-3 text-sm font-semibold transition">
                Lưu hồ sơ
              </button>
            </AppCard>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
