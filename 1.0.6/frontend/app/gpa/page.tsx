"use client";

import { Calculator, ChartNoAxesColumnIncreasing, History, ListPlus, RotateCcw, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { calculateGpa, getGpaHistory, simulateGpa, type GpaCourseInput } from "@/lib/api";

type GpaTab = "nhap-lieu" | "ket-qua" | "lich-su" | "quy-doi";
type GpaRowResult = {
  course_code?: string | null;
  name?: string | null;
  credits?: number;
  grade?: string | null;
  numeric_grade?: number | null;
  counted?: boolean;
};
type GpaHistoryTerm = {
  semester_code?: string;
  credits?: number;
  gpa?: number | null;
  courses?: GpaRowResult[];
};

const defaultRows: GpaCourseInput[] = [
  { course_code: "NT208", name: "Lập trình ứng dụng Web", credits: 3, grade: "A" },
  { course_code: "NT219", name: "An toàn mạng", credits: 3, grade: "B+" },
  { course_code: "SS004", name: "Kỹ năng nghề nghiệp", credits: 2, grade: "A+" },
];

const GPA_TABS: Array<{
  id: GpaTab;
  label: string;
  description: string;
  icon: typeof Calculator;
}> = [
  { id: "nhap-lieu", label: "Nhập liệu", description: "Môn và điểm", icon: ListPlus },
  { id: "ket-qua", label: "Kết quả", description: "GPA học kỳ", icon: Calculator },
  { id: "lich-su", label: "Lịch sử", description: "Các học kỳ trước", icon: History },
  { id: "quy-doi", label: "Quy đổi", description: "Thang điểm demo", icon: ChartNoAxesColumnIncreasing },
];

const gradeScale = [
  ["A+", "10.0"],
  ["A", "9.0"],
  ["B+", "8.0"],
  ["B", "7.0"],
  ["C+", "6.5"],
  ["C", "5.5"],
  ["D+", "5.0"],
  ["D", "4.0"],
  ["F", "0.0"],
];

function displayValue(value: unknown, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function numberValue(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
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
  icon: typeof Calculator;
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

function TabNavigation({ activeTab, onChange }: { activeTab: GpaTab; onChange: (tab: GpaTab) => void }) {
  return (
    <div
      role="tablist"
      aria-label="Nhóm nội dung GPA"
      className="grid gap-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-2 md:grid-cols-2 xl:grid-cols-4"
    >
      {GPA_TABS.map((tab) => {
        const Icon = tab.icon;
        const selected = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            id={`gpa-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`gpa-panel-${tab.id}`}
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

export default function GpaPage() {
  const [activeTab, setActiveTab] = useState<GpaTab>("nhap-lieu");
  const [rows, setRows] = useState<GpaCourseInput[]>(defaultRows);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [simulation, setSimulation] = useState<Record<string, unknown> | null>(null);
  const [history, setHistory] = useState<GpaHistoryTerm[]>([]);
  const [busy, setBusy] = useState<"calculate" | "simulate" | "">("");
  const [error, setError] = useState("");

  useEffect(() => {
    getGpaHistory().then((payload) => setHistory(payload as GpaHistoryTerm[]));
  }, []);

  const totalCredits = useMemo(() => rows.reduce((sum, row) => sum + numberValue(row.credits), 0), [rows]);
  const resultRows = ((result?.rows as GpaRowResult[] | undefined) ?? []);
  const countedCredits = numberValue(result?.counted_credits);
  const projectedGpa = simulation?.projected_cumulative_gpa;
  const semesterGpa = result?.gpa ?? simulation?.semester_gpa;

  function updateRow(index: number, patch: Partial<GpaCourseInput>) {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  function removeRow(index: number) {
    setRows((current) => current.filter((_, rowIndex) => rowIndex !== index));
  }

  async function runCalculate() {
    try {
      setBusy("calculate");
      setError("");
      const payload = await calculateGpa(rows);
      setResult(payload);
      setActiveTab("ket-qua");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Không tính được GPA.");
    } finally {
      setBusy("");
    }
  }

  async function runSimulate() {
    try {
      setBusy("simulate");
      setError("");
      const payload = await simulateGpa(rows);
      setSimulation(payload);
      setResult((current) => current ?? { gpa: payload.semester_gpa, counted_credits: payload.planned_counted_credits, rows: [] });
      setActiveTab("ket-qua");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Không mô phỏng được GPA tích lũy.");
    } finally {
      setBusy("");
    }
  }

  return (
    <AppShell pageTitle="Công cụ GPA" pageDescription="Tính GPA học kỳ, mô phỏng GPA tích lũy và xem lịch sử điểm theo từng tab.">
      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Môn đang nhập" value={`${rows.length}`} hint="Dòng hiện tại" icon={ListPlus} />
        <MetricTile label="Tổng tín chỉ" value={`${totalCredits}`} hint="Theo form" icon={ChartNoAxesColumnIncreasing} />
        <MetricTile label="GPA học kỳ" value={displayValue(semesterGpa)} hint={`${countedCredits} TC tính điểm`} icon={Calculator} />
        <MetricTile label="GPA dự phóng" value={displayValue(projectedGpa)} hint="Sau mô phỏng" icon={Sparkles} />
      </section>

      <AppCard
        title="Tóm tắt nhanh"
        subtitle="Nhập điểm ở tab đầu tiên, sau đó chuyển sang kết quả để kiểm tra từng dòng được tính hay bỏ qua."
        action={<Badge tone={result?.gpa ? "accent" : "default"}>{result?.gpa ? "Đã có kết quả" : "Chưa tính"}</Badge>}
      >
        <div className="grid gap-3 md:grid-cols-3">
          <button
            type="button"
            onClick={() => setActiveTab("nhap-lieu")}
            className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-left transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]"
          >
            <ListPlus className="h-5 w-5 text-[color:var(--accent)]" />
            <p className="mt-3 font-semibold text-[color:var(--text-primary)]">Cập nhật môn học</p>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Thêm môn, sửa tín chỉ hoặc nhập chữ điểm thang UIT demo.</p>
          </button>
          <button
            type="button"
            onClick={() => void runCalculate()}
            disabled={busy !== ""}
            className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-left transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)] disabled:opacity-60"
          >
            <Calculator className="h-5 w-5 text-[color:var(--accent)]" />
            <p className="mt-3 font-semibold text-[color:var(--text-primary)]">{busy === "calculate" ? "Đang tính..." : "Tính GPA học kỳ"}</p>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Chỉ tính các môn có điểm hợp lệ và tín chỉ lớn hơn 0.</p>
          </button>
          <button
            type="button"
            onClick={() => void runSimulate()}
            disabled={busy !== ""}
            className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-left transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)] disabled:opacity-60"
          >
            <Sparkles className="h-5 w-5 text-[color:var(--accent)]" />
            <p className="mt-3 font-semibold text-[color:var(--text-primary)]">{busy === "simulate" ? "Đang mô phỏng..." : "Mô phỏng tích lũy"}</p>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Ghép điểm dự kiến với lịch sử học tập đang có trong hồ sơ.</p>
          </button>
        </div>
      </AppCard>

      <TabNavigation activeTab={activeTab} onChange={setActiveTab} />

      <div id={`gpa-panel-${activeTab}`} role="tabpanel" aria-labelledby={`gpa-tab-${activeTab}`} className="space-y-4">
        {activeTab === "nhap-lieu" ? (
          <AppCard
            title="Nhập môn học"
            subtitle="Có thể nhập chữ điểm A/B hoặc điểm số thang 10 ở trường điểm."
            action={
              <button
                type="button"
                onClick={() => setRows(defaultRows)}
                className="inline-flex h-10 items-center gap-2 rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[color:var(--accent-soft)]"
              >
                <RotateCcw className="h-4 w-4" />
                Mẫu
              </button>
            }
          >
            <div className="space-y-3">
              {rows.length === 0 ? (
                <EmptyState>Chưa có dòng môn học nào.</EmptyState>
              ) : (
                rows.map((row, index) => (
                  <div
                    key={index}
                    className="grid gap-3 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 md:grid-cols-[0.75fr_1.1fr_0.35fr_0.4fr_auto]"
                  >
                    <input
                      value={row.course_code ?? ""}
                      onChange={(event) => updateRow(index, { course_code: event.target.value })}
                      className="rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-[color:var(--accent)]"
                      placeholder="Mã môn"
                    />
                    <input
                      value={row.name ?? ""}
                      onChange={(event) => updateRow(index, { name: event.target.value })}
                      className="rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-[color:var(--accent)]"
                      placeholder="Tên môn"
                    />
                    <input
                      value={row.credits}
                      type="number"
                      min={0}
                      max={20}
                      onChange={(event) => updateRow(index, { credits: Number(event.target.value) })}
                      className="rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-[color:var(--accent)]"
                      placeholder="TC"
                    />
                    <input
                      value={row.grade ?? ""}
                      onChange={(event) => updateRow(index, { grade: event.target.value })}
                      className="rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-[color:var(--accent)]"
                      placeholder="Điểm"
                    />
                    <button
                      type="button"
                      onClick={() => removeRow(index)}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] text-[color:var(--text-muted)] transition hover:border-[color:var(--badge-danger-border)] hover:bg-[color:var(--badge-danger-bg)] hover:text-[color:var(--badge-danger-text)]"
                      aria-label={`Xóa dòng ${index + 1}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" onClick={() => setRows((current) => [...current, { credits: 3, grade: "B" }])} className="btn-secondary rounded-md px-5 py-3 text-sm font-semibold transition">
                Thêm dòng
              </button>
              <button type="button" onClick={() => void runCalculate()} disabled={busy !== ""} className="btn-primary rounded-md px-5 py-3 text-sm font-semibold transition disabled:opacity-60">
                {busy === "calculate" ? "Đang tính..." : "Tính GPA"}
              </button>
              <button type="button" onClick={() => void runSimulate()} disabled={busy !== ""} className="btn-secondary rounded-md px-5 py-3 text-sm font-semibold transition disabled:opacity-60">
                {busy === "simulate" ? "Đang mô phỏng..." : "Mô phỏng tích lũy"}
              </button>
            </div>
          </AppCard>
        ) : null}

        {activeTab === "ket-qua" ? (
          <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
            <AppCard title="Kết quả GPA" subtitle="Chỉ tính các môn có điểm hợp lệ.">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm text-[color:var(--text-muted)]">GPA học kỳ</p>
                  <p className="mt-2 text-4xl font-semibold text-[color:var(--text-primary)]">{displayValue(result?.gpa)}</p>
                </div>
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm text-[color:var(--text-muted)]">Tín chỉ tính điểm</p>
                  <p className="mt-2 text-4xl font-semibold text-[color:var(--text-primary)]">{displayValue(result?.counted_credits, "0")}</p>
                </div>
              </div>

              <div className="mt-3 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <p className="text-sm text-[color:var(--text-muted)]">GPA tích lũy dự phóng</p>
                <p className="mt-2 text-3xl font-semibold text-[color:var(--text-primary)]">{displayValue(simulation?.projected_cumulative_gpa)}</p>
                <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                  {displayValue(simulation?.note, "Bấm mô phỏng tích lũy để ghép học kỳ hiện tại với lịch sử trong hồ sơ.")}
                </p>
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm text-[color:var(--text-muted)]">Tín chỉ đã có</p>
                  <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{displayValue(simulation?.existing_counted_credits, "0")}</p>
                </div>
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="text-sm text-[color:var(--text-muted)]">Tín chỉ dự kiến</p>
                  <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{displayValue(simulation?.planned_counted_credits, "0")}</p>
                </div>
              </div>
            </AppCard>

            <AppCard title="Chi tiết từng dòng" subtitle="Kiểm tra môn nào được tính vào GPA và môn nào bị bỏ qua.">
              <div className="space-y-3">
                {resultRows.length === 0 ? (
                  <EmptyState>Chưa có chi tiết. Hãy bấm Tính GPA hoặc Mô phỏng tích lũy.</EmptyState>
                ) : (
                  resultRows.map((row, index) => (
                    <div key={`${row.course_code ?? "row"}-${index}`} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="font-semibold text-[color:var(--text-primary)]">
                            {displayValue(row.course_code, "Môn chưa mã")} • {displayValue(row.name, "Chưa nhập tên")}
                          </p>
                          <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                            {displayValue(row.credits, "0")} tín chỉ • Điểm số {displayValue(row.numeric_grade)}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2 sm:justify-end">
                          <Badge tone={row.counted ? "success" : "default"}>{row.counted ? "Được tính" : "Bỏ qua"}</Badge>
                          <Badge tone="accent">{displayValue(row.grade)}</Badge>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </AppCard>
          </div>
        ) : null}

        {activeTab === "lich-su" ? (
          <AppCard title="Lịch sử GPA" subtitle="Đọc từ kết quả học tập seed/demo của sinh viên.">
            <div className="grid gap-4 xl:grid-cols-2">
              {history.length === 0 ? (
                <div className="xl:col-span-2">
                  <EmptyState>Chưa có lịch sử GPA.</EmptyState>
                </div>
              ) : (
                history.map((term) => (
                  <div key={String(term.semester_code)} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[color:var(--text-primary)]">{displayValue(term.semester_code, "Học kỳ")}</p>
                        <p className="mt-2 text-sm text-[color:var(--text-muted)]">{displayValue(term.credits, "0")} tín chỉ tính điểm</p>
                      </div>
                      <Badge tone="accent">GPA {displayValue(term.gpa)}</Badge>
                    </div>
                    <div className="mt-4 space-y-2">
                      {(term.courses ?? []).slice(0, 4).map((course, index) => (
                        <div key={`${course.course_code ?? "course"}-${index}`} className="rounded-md bg-[color:var(--surface)] px-3 py-3 text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-medium text-[color:var(--text-primary)]">{displayValue(course.course_code)} • {displayValue(course.name)}</span>
                            <span className="text-[color:var(--text-muted)]">{displayValue(course.grade)} / {displayValue(course.numeric_grade)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </AppCard>
        ) : null}

        {activeTab === "quy-doi" ? (
          <div className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
            <AppCard title="Thang điểm đang dùng" subtitle="Bản demo dùng quy đổi chữ điểm sang thang 10 để tính nhanh.">
              <div className="grid grid-cols-3 gap-3">
                {gradeScale.map(([letter, score]) => (
                  <div key={letter} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-center">
                    <p className="text-sm text-[color:var(--text-muted)]">{letter}</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{score}</p>
                  </div>
                ))}
              </div>
            </AppCard>

            <AppCard title="Cách đọc kết quả" subtitle="Giữ phần này để demo với giảng viên rõ hơn khi nhập nhiều kịch bản điểm.">
              <div className="space-y-3">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="font-semibold text-[color:var(--text-primary)]">GPA học kỳ</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Tổng điểm quy đổi nhân tín chỉ, chia cho số tín chỉ của các môn có điểm hợp lệ.</p>
                </div>
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="font-semibold text-[color:var(--text-primary)]">GPA tích lũy dự phóng</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Ghép tín chỉ và điểm dự kiến kỳ này với lịch sử học tập đã có trong hồ sơ sinh viên.</p>
                </div>
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <p className="font-semibold text-[color:var(--text-primary)]">Môn bị bỏ qua</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Môn không có điểm hợp lệ hoặc tín chỉ bằng 0 sẽ không được tính vào GPA.</p>
                </div>
              </div>
            </AppCard>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
