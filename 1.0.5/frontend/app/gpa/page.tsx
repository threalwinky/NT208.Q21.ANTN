"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { calculateGpa, getGpaHistory, simulateGpa, type GpaCourseInput } from "@/lib/api";

const defaultRows: GpaCourseInput[] = [
  { course_code: "NT208", name: "Lập trình ứng dụng Web", credits: 3, grade: "A" },
  { course_code: "NT219", name: "An toàn mạng", credits: 3, grade: "B+" },
  { course_code: "SS004", name: "Kỹ năng nghề nghiệp", credits: 2, grade: "A+" },
];

export default function GpaPage() {
  const [rows, setRows] = useState<GpaCourseInput[]>(defaultRows);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [simulation, setSimulation] = useState<Record<string, unknown> | null>(null);
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    getGpaHistory().then(setHistory);
  }, []);

  function updateRow(index: number, patch: Partial<GpaCourseInput>) {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <AppShell pageTitle="Công cụ GPA" pageDescription="Tính nhanh GPA học kỳ và mô phỏng tác động lên GPA tích lũy theo thang 10.">
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <AppCard title="Nhập môn học" subtitle="Có thể nhập chữ điểm A/B hoặc điểm số thang 10.">
          <div className="space-y-3">
            {rows.map((row, index) => (
              <div key={index} className="grid gap-3 rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 md:grid-cols-[0.7fr_1fr_0.35fr_0.35fr]">
                <input value={row.course_code ?? ""} onChange={(event) => updateRow(index, { course_code: event.target.value })} className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm outline-none" placeholder="Mã môn" />
                <input value={row.name ?? ""} onChange={(event) => updateRow(index, { name: event.target.value })} className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm outline-none" placeholder="Tên môn" />
                <input value={row.credits} type="number" onChange={(event) => updateRow(index, { credits: Number(event.target.value) })} className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm outline-none" placeholder="TC" />
                <input value={row.grade ?? ""} onChange={(event) => updateRow(index, { grade: event.target.value })} className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm outline-none" placeholder="Điểm" />
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={() => setRows((current) => [...current, { credits: 3, grade: "B" }])} className="btn-secondary rounded-2xl px-5 py-3 text-sm font-semibold transition">Thêm dòng</button>
            <button type="button" onClick={async () => setResult(await calculateGpa(rows))} className="btn-primary rounded-2xl px-5 py-3 text-sm font-semibold transition">Tính GPA</button>
            <button type="button" onClick={async () => setSimulation(await simulateGpa(rows))} className="btn-secondary rounded-2xl px-5 py-3 text-sm font-semibold transition">Mô phỏng tích lũy</button>
          </div>
        </AppCard>

        <div className="space-y-4">
          <AppCard title="Kết quả" subtitle="Chỉ tính các môn có điểm hợp lệ.">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <p className="text-sm text-[color:var(--text-muted)]">GPA học kỳ</p>
                <p className="mt-2 text-3xl font-semibold">{String(result?.gpa ?? "--")}</p>
              </div>
              <div className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <p className="text-sm text-[color:var(--text-muted)]">Tín chỉ tính điểm</p>
                <p className="mt-2 text-3xl font-semibold">{String(result?.counted_credits ?? 0)}</p>
              </div>
            </div>
            {simulation ? <p className="mt-4 rounded-2xl bg-[color:var(--accent-soft)] px-4 py-3 text-sm text-[color:var(--accent)]">GPA tích lũy dự phóng: {String(simulation.projected_cumulative_gpa ?? "--")}</p> : null}
          </AppCard>
          <AppCard title="Lịch sử GPA" subtitle="Đọc từ kết quả học tập seed/demo của sinh viên.">
            <div className="space-y-3">
              {history.map((term) => (
                <div key={String(term.semester_code)} className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{String(term.semester_code)}</p>
                    <Badge tone="accent">GPA {String(term.gpa ?? "--")}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">{String(term.credits)} tín chỉ tính điểm</p>
                </div>
              ))}
            </div>
          </AppCard>
        </div>
      </div>
    </AppShell>
  );
}
