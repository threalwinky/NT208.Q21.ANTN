"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { getAcademicEvents, getStudyDocuments } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function AcademicPage() {
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    getStudyDocuments().then(setDocuments);
    getAcademicEvents().then(setEvents);
  }, []);

  return (
    <AppShell
      pageTitle="Trung tâm học vụ"
      pageDescription="Tập trung tài liệu, thủ tục, mốc học vụ và hướng dẫn dành riêng cho sinh viên UIT đang học."
    >
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <AppCard title="Kho tài liệu học vụ" subtitle="Tài liệu được lọc theo nội dung học vụ, thủ tục, xét tốt nghiệp và học phí.">
          <div className="space-y-3">
            {documents.map((item) => (
              <a
                key={String(item.id)}
                href={String(item.url)}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <p className="font-medium">{String(item.title)}</p>
                  <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>
                    {Boolean(item.is_official_uit) ? "Nguồn UIT" : "Tham khảo"}
                  </Badge>
                </div>
                <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{String(item.summary ?? "")}</p>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-[color:var(--text-soft)]">
                  <span>{String(item.group_name ?? "Tài liệu")}</span>
                  <span>•</span>
                  <span>{formatDate(String(item.updated_source_at ?? ""))}</span>
                </div>
              </a>
            ))}
          </div>
        </AppCard>

        <AppCard title="Mốc học vụ sắp tới" subtitle="Những cột mốc nên chốt sớm để không bị dồn việc vào phút cuối.">
          <div className="space-y-3">
            {events.map((item) => (
              <div key={String(item.id)} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex items-center justify-between gap-4">
                  <p className="font-medium">{String(item.title)}</p>
                  <Badge tone="accent">{String(item.group_name)}</Badge>
                </div>
                <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{String(item.description ?? "")}</p>
                <p className="mt-4 text-sm text-[color:var(--text-soft)]">
                  {formatDate(String(item.starts_at ?? ""))}
                  {item.ends_at ? ` - ${formatDate(String(item.ends_at))}` : ""}
                </p>
              </div>
            ))}
          </div>
        </AppCard>
      </div>
    </AppShell>
  );
}
