"use client";

import { AlertTriangle, CheckCircle2, Clock3, GraduationCap, Route } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { PrerequisiteGraph } from "@/components/prerequisite-graph";
import { AppCard, Badge, StatCard } from "@/components/ui";
import { getAdvisorOverview, getProfile, updateProfile, type AdvisorOverview, type Profile } from "@/lib/api";

function statusTone(status: string): "default" | "accent" | "warn" | "danger" | "success" {
  if (status === "PASSED" || status === "WAIVED") {
    return "success";
  }
  if (status === "IN_PROGRESS") {
    return "accent";
  }
  if (status === "FAILED") {
    return "danger";
  }
  if (status === "PLANNED" || status === "PLANNED_NEXT") {
    return "warn";
  }
  return "default";
}

export default function AdvisorPage() {
  const [data, setData] = useState<AdvisorOverview | null>(null);
  const [error, setError] = useState("");

  // --- Hồ sơ sinh viên ---
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
    getProfile().then((payload) => {
      setProfile(payload);
      setForm(payload);
    });
  }, []);

  async function save() {
    const updated = await updateProfile(form);
    setProfile(updated);
    setForm(updated);
    setSaveMsg("Đã lưu hồ sơ.");
  }

  const priorityCourses = useMemo(
    () =>
      (data?.degree_audit.required_courses ?? [])
        .filter((course) => !["PASSED", "WAIVED"].includes(course.status))
        .slice(0, 8),
    [data],
  );

  const riskTone = data?.academic_risk.risk_level === "HIGH" ? "danger" : data?.academic_risk.risk_level === "MEDIUM" ? "warn" : "success";

  return (
    <AppShell
      pageTitle="Học tập"
      pageDescription="Lộ trình học, tiến độ môn học và hồ sơ sinh viên."
    >
      {error ? (
        <div className="rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <AppCard
          title="Hồ sơ đang theo dõi"
          subtitle="Studify dùng hồ sơ học tập, CTĐT và kết quả hiện tại để đưa gợi ý."
          action={<Badge tone="accent">{data?.degree_audit.identity.cohort_label ?? "Đang đồng bộ"}</Badge>}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Sinh viên</p>
              <p className="mt-2 text-lg font-semibold">{data?.degree_audit.identity.student_name ?? "..."}</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                MSSV {data?.degree_audit.identity.student_id ?? "..."} • {data?.degree_audit.identity.class_name ?? "..."}
              </p>
            </div>
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Ngành học</p>
              <p className="mt-2 text-lg font-semibold">{data?.degree_audit.program_name ?? "..."}</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                {data?.degree_audit.identity.faculty ?? "..."} • Dự kiến {data?.degree_audit.identity.expected_graduation_term ?? "..."}
              </p>
            </div>
          </div>
        </AppCard>

        <AppCard
          title="Cảnh báo học tập"
          subtitle="Điểm rủi ro được đọc từ GPA, môn nợ, task quá hạn và nhịp học gần đây."
          action={<Badge tone={riskTone}>{data?.academic_risk.risk_level ?? "LOW"}</Badge>}
        >
          <div className="space-y-3">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Tóm tắt</p>
              <p className="mt-2 text-base font-medium">{data?.academic_risk.summary ?? "Đang phân tích..."}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <p className="text-sm text-[color:var(--text-muted)]">Risk score</p>
                <p className="mt-2 text-2xl font-semibold">{data?.academic_risk.risk_score ?? 0}</p>
              </div>
              <div className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <p className="text-sm text-[color:var(--text-muted)]">Môn nợ</p>
                <p className="mt-2 text-2xl font-semibold">{data?.academic_risk.failed_course_count ?? 0}</p>
              </div>
              <div className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <p className="text-sm text-[color:var(--text-muted)]">Task quá hạn</p>
                <p className="mt-2 text-2xl font-semibold">{data?.academic_risk.overdue_task_count ?? 0}</p>
              </div>
            </div>
          </div>
        </AppCard>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Tiến độ CTĐT" value={`${data?.degree_audit.completion_percent ?? 0}%`} hint="Dựa trên degree audit" />
        <StatCard label="Tín chỉ còn lại" value={`${data?.degree_audit.remaining_credits ?? 0}`} hint="Cần khép để đủ chuẩn" />
        <StatCard label="Tải học kỳ gợi ý" value={`${data?.semester_planning.recommended_credit_load ?? 0} TC`} hint="Điều chỉnh theo risk" />
        <StatCard label="Môn đang chặn" value={`${data?.semester_planning.blocking_courses.length ?? 0}`} hint="Tiên quyết chưa khép" />
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.02fr_0.98fr]">
        <AppCard
          title="Tiến độ CTĐT"
          subtitle="Bạn đang ở đâu trong CTĐT và các nhóm tín chỉ đang thiếu."
          action={<Badge tone="accent">{data?.degree_audit.passed_credits ?? 0}/{data?.degree_audit.total_required_credits ?? 0} TC</Badge>}
        >
          <div className="space-y-4">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex items-center justify-between gap-4 text-sm">
                <span className="text-[color:var(--text-muted)]">Tiến độ hoàn thành</span>
                <span className="font-semibold text-[color:var(--text-primary)]">{data?.degree_audit.completion_percent ?? 0}%</span>
              </div>
              <div className="mt-3 h-3 rounded-full bg-[color:var(--surface-strong)]">
                <div
                  className="h-3 rounded-full bg-[color:var(--accent)]"
                  style={{ width: `${Math.min(100, data?.degree_audit.completion_percent ?? 0)}%` }}
                />
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{data?.degree_audit.milestone_summary}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {(data?.degree_audit.category_progress ?? []).map((item) => (
                <div key={item.category} className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm font-medium">{item.category}</p>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                    {item.passed_credits}/{item.required_credits} tín chỉ
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[color:var(--text-soft)]">Còn {item.remaining_credits} TC</p>
                </div>
              ))}
            </div>

            <div>
              <p className="text-sm font-medium">Môn ưu tiên tiếp theo</p>
              <div className="mt-3 space-y-3">
                {priorityCourses.map((course) => (
                  <div key={course.course_id} className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">{course.code} • {course.name}</p>
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
                ))}
              </div>
            </div>
          </div>
        </AppCard>

        <AppCard
          title="Cảnh báo học tập"
          subtitle="Nhìn nhanh các tín hiệu đang kéo rủi ro lên và các bước hạ nhiệt ngay."
          action={<Badge tone={riskTone}>{data?.academic_risk.risk_score ?? 0} điểm</Badge>}
        >
          <div className="grid gap-4">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                <AlertTriangle className="h-4 w-4 text-[color:var(--accent)]" />
                Tín hiệu đang theo dõi
              </div>
              <div className="mt-3 space-y-2">
                {(data?.academic_risk.signals ?? []).map((signal) => (
                  <div key={signal} className="rounded-2xl bg-[color:var(--surface)] px-3 py-3 text-sm leading-6">
                    {signal}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                <CheckCircle2 className="h-4 w-4 text-[color:var(--accent)]" />
                Bước nên làm ngay
              </div>
              <div className="mt-3 space-y-2">
                {(data?.academic_risk.recommendations ?? []).map((item) => (
                  <div key={item} className="rounded-2xl bg-[color:var(--surface)] px-3 py-3 text-sm leading-6">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </AppCard>
      </div>

      <AppCard
        title="Sơ đồ tiên quyết"
        subtitle="Mỗi mũi tên là một ràng buộc tiên quyết; màu trạng thái cho biết nên chốt môn nào trước."
        action={
          <Badge tone={data?.semester_planning.blocking_courses.length ? "warn" : "success"}>
            {data?.semester_planning.blocking_courses.length ? `${data?.semester_planning.blocking_courses.length} môn đang chặn` : "Luồng học đang thông"}
          </Badge>
        }
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
          <PrerequisiteGraph
            nodes={data?.semester_planning.graph_nodes ?? []}
            edges={data?.semester_planning.graph_edges ?? []}
          />
          {data?.semester_planning.blocking_courses.length ? (
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-sm leading-6 text-[color:var(--text-muted)]">
              Các môn đang chặn luồng hiện tại: {data.semester_planning.blocking_courses.join(", ")}.
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
          {(data?.semester_planning.semesters ?? []).map((semester) => (
            <div key={semester.semester_code} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{semester.title}</p>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                    {semester.semester_code} • {semester.total_credits}/{semester.max_credits} tín chỉ
                  </p>
                </div>
                <Badge tone="accent">{semester.total_credits} TC</Badge>
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{semester.notes}</p>
              <div className="mt-4 space-y-3">
                {semester.courses.map((course) => (
                  <div key={course.course_id} className="rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface)] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="font-medium">{course.code} • {course.name}</p>
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
          ))}
        </div>
      </AppCard>

      {/* ── Hồ sơ sinh viên ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 pt-4">
        <h2 className="text-xl font-semibold">Hồ sơ sinh viên</h2>
        <p className="text-sm text-[color:var(--text-muted)]">
          Thông tin cá nhân và học vụ được Studify dùng để cá nhân hóa gợi ý học kỳ, cố vấn học tập và trải nghiệm trong app.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <AppCard title="Tóm tắt" subtitle="Studify chỉ dùng hồ sơ này để cá nhân hóa trải nghiệm trong app.">
          <div className="space-y-4">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Tài khoản</p>
              <p className="mt-2 text-xl font-semibold">{profile?.full_name ?? "Đang tải..."}</p>
              <p className="mt-1 text-sm text-[color:var(--text-soft)]">@{profile?.username ?? "studify"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="accent">{profile?.role ?? "STUDENT"}</Badge>
              <Badge tone="success">{profile?.student_id ? `MSSV ${profile.student_id}` : "Chưa có MSSV"}</Badge>
            </div>
            {saveMsg ? (
              <p className="rounded-2xl bg-[color:var(--accent-soft)] px-4 py-3 text-sm text-[color:var(--accent)]">{saveMsg}</p>
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
                  className="mt-2 w-full rounded-[14px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2.5 text-sm outline-none"
                />
              </label>
            ))}
          </div>
          <button type="button" onClick={save} className="btn-primary mt-5 rounded-2xl px-5 py-3 text-sm font-semibold transition">
            Lưu hồ sơ
          </button>
        </AppCard>
      </div>
    </AppShell>
  );
}
