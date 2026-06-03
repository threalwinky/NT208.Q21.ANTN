"use client";

import { Bookmark } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { getAnnouncements, toggleSaveAnnouncement } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function AnnouncementPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);

  async function refresh() {
    const data = await getAnnouncements();
    setItems(data);
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      const data = await getAnnouncements();
      if (mounted) {
        setItems(data);
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell
      pageTitle="Bảng thông báo UIT"
      pageDescription="Gom các bài quan trọng theo nhóm học vụ, CTSV, học bổng, tâm lý và kỹ năng để bạn không cần mở nhiều cổng cùng lúc."
    >
      <AppCard title="Thông báo mới nhất" subtitle="Có thể lưu lại để đọc sau khi bạn đang bận học hoặc bận deadline.">
        <div className="grid gap-4 xl:grid-cols-2">
          {items.map((item) => (
            <div key={String(item.id)} className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium">{String(item.title)}</p>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{String(item.shortDescription ?? "")}</p>
                </div>
                <Badge tone={Boolean(item.isOfficialUit) ? "success" : "warn"}>
                  {Boolean(item.isOfficialUit) ? "UIT" : "Tham khảo"}
                </Badge>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm text-[color:var(--text-soft)]">
                  {String(item.groupName)} • {formatDate(String(item.publishedAt ?? ""))}
                </div>
                <div className="flex flex-wrap items-stretch gap-2">
                  <button
                    type="button"
                    onClick={async () => {
                      await toggleSaveAnnouncement(Number(item.id));
                      await refresh();
                    }}
                    className="btn-secondary inline-flex h-11 min-w-[116px] items-center gap-2 rounded-lg px-4 text-sm font-medium transition"
                  >
                    <Bookmark className="h-4 w-4" />
                    {Boolean(item.isSaved) ? "Bỏ lưu" : "Lưu lại"}
                  </button>
                  <a
                    href={String(item.url)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-primary inline-flex h-11 min-w-[116px] rounded-lg px-4 text-sm font-semibold transition"
                  >
                    Mở nguồn
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      </AppCard>
    </AppShell>
  );
}
