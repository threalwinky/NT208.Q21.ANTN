"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { getCourses, type Course } from "@/lib/api";

export default function CoursesPage() {
  const [query, setQuery] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);

  async function load(q = query) {
    setCourses(await getCourses(q));
  }

  useEffect(() => {
    let mounted = true;
    getCourses("").then((data) => {
      if (mounted) {
        setCourses(data);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell pageTitle="Danh mục môn học" pageDescription="Tra cứu học phần, tín chỉ, nhóm yêu cầu và tiên quyết trong CTĐT demo.">
      <AppCard title="Tìm môn học" subtitle="Có thể tìm bằng mã môn hoặc tên môn.">
        <div className="flex flex-col gap-3 md:flex-row">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ví dụ: NT208, cơ sở dữ liệu, an toàn mạng..."
            className="min-h-12 flex-1 rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm outline-none"
          />
          <button type="button" onClick={() => void load()} className="btn-primary rounded-lg px-5 py-3 text-sm font-semibold transition">
            Tìm kiếm
          </button>
        </div>
      </AppCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {courses.map((course) => (
          <div key={course.id} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Badge tone="accent">{course.code}</Badge>
              <Badge tone="default">{course.credits} tín chỉ</Badge>
            </div>
            <h2 className="mt-4 text-lg font-semibold">{course.name}</h2>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{course.description ?? "Chưa có mô tả chi tiết."}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="success">{course.category}</Badge>
              {course.requirement_groups.map((group) => (
                <Badge key={group} tone="default">{group}</Badge>
              ))}
            </div>
            {course.prerequisite_codes.length ? <p className="mt-4 text-sm text-[color:var(--text-soft)]">Tiên quyết: {course.prerequisite_codes.join(", ")}</p> : null}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
