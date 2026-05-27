"use client";

import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { searchStudify } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("đăng ký học phần");
  const [result, setResult] = useState<Record<string, Array<Record<string, unknown>> | string> | null>(null);

  async function runSearch() {
    setResult(await searchStudify(query));
  }

  const documents = (result?.documents as Array<Record<string, unknown>> | undefined) ?? [];
  const announcements = (result?.announcements as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <AppShell pageTitle="Tìm kiếm Studify" pageDescription="Tìm đồng thời trong tài liệu tri thức và bảng thông báo đã chuẩn hóa.">
      <AppCard title="Tìm nhanh" subtitle="Phù hợp khi cần kiểm nguồn trước khi hỏi chatbot.">
        <div className="flex flex-col gap-3 md:flex-row">
          <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-h-12 flex-1 rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm outline-none" />
          <button type="button" onClick={runSearch} className="btn-primary rounded-2xl px-5 py-3 text-sm font-semibold transition">Tìm</button>
        </div>
      </AppCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <AppCard title="Tài liệu" subtitle={`${documents.length} kết quả`}>
          <div className="space-y-3">
            {documents.map((item) => (
              <a key={`doc-${String(item.id)}`} href={String(item.url)} target="_blank" rel="noreferrer" className="block rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>{Boolean(item.is_official_uit) ? "UIT" : "Tham khảo"}</Badge>
                <p className="mt-3 font-medium">{String(item.title)}</p>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{String(item.summary ?? "")}</p>
              </a>
            ))}
          </div>
        </AppCard>
        <AppCard title="Thông báo" subtitle={`${announcements.length} kết quả`}>
          <div className="space-y-3">
            {announcements.map((item) => (
              <a key={`ann-${String(item.id)}`} href={String(item.url)} target="_blank" rel="noreferrer" className="block rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <Badge tone="accent">{String(item.group_name ?? "Thông báo")}</Badge>
                <p className="mt-3 font-medium">{String(item.title)}</p>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{String(item.summary ?? "")}</p>
              </a>
            ))}
          </div>
        </AppCard>
      </div>
    </AppShell>
  );
}
