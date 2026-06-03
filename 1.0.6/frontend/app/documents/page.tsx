"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { getDocuments } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function DocumentsPage() {
  const [query, setQuery] = useState("");
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);

  async function load(q = query) {
    setDocuments(await getDocuments(q));
  }

  useEffect(() => {
    let mounted = true;
    getDocuments("").then((data) => {
      if (mounted) {
        setDocuments(data);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell pageTitle="Tài liệu tri thức" pageDescription="Duyệt tài liệu đã crawl/tải lên và kiểm nhanh độ chính thức của nguồn.">
      <AppCard title="Lọc tài liệu" subtitle="Tìm trong title, summary và nội dung đã làm sạch.">
        <div className="flex flex-col gap-3 md:flex-row">
          <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-h-12 flex-1 rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm outline-none" placeholder="Tìm học phí, tốt nghiệp, học bổng..." />
          <button type="button" onClick={() => void load()} className="btn-primary rounded-lg px-5 py-3 text-sm font-semibold transition">Tìm tài liệu</button>
        </div>
      </AppCard>
      <div className="grid gap-4 xl:grid-cols-2">
        {documents.map((item) => (
          <a key={String(item.id)} href={String(item.url)} target="_blank" rel="noreferrer" className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-sm transition hover:border-[color:var(--accent)]/30">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>{Boolean(item.is_official_uit) ? "Nguồn UIT" : "Tham khảo"}</Badge>
              <Badge tone="default">{String(item.group_name ?? "Tài liệu")}</Badge>
            </div>
            <h2 className="mt-4 text-lg font-semibold">{String(item.title)}</h2>
            <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{String(item.summary ?? "Chưa có tóm tắt.")}</p>
            <p className="mt-4 text-sm text-[color:var(--text-soft)]">Cập nhật: {formatDate(String(item.updated_source_at ?? ""))}</p>
          </a>
        ))}
      </div>
    </AppShell>
  );
}
