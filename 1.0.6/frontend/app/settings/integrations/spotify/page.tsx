"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { connectSpotifyPreview, disconnectSpotify, getSpotifyStatus, type SpotifyStatus } from "@/lib/api";

export default function SpotifyIntegrationPage() {
  const [status, setStatus] = useState<SpotifyStatus | null>(null);
  const [displayName, setDisplayName] = useState("Studify demo");

  useEffect(() => {
    let mounted = true;
    getSpotifyStatus().then((data) => {
      if (mounted) {
        setStatus(data);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell pageTitle="Tích hợp Spotify" pageDescription="Spotify là tùy chọn; demo vẫn chạy bằng curated playlist khi chưa cấu hình secret.">
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <AppCard title="Trạng thái" subtitle="Backend không lưu refresh token dài hạn trong bản demo này.">
          <div className="space-y-3">
            <Badge tone={status?.enabled ? "success" : "warn"}>{status?.enabled ? "Spotify API bật" : "Dùng curated fallback"}</Badge>
            <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Kết nối tài khoản</p>
              <p className="mt-2 text-xl font-semibold">{status?.connected ? status.display_name ?? "Đã kết nối" : "Chưa kết nối"}</p>
            </div>
          </div>
        </AppCard>
        <AppCard title="Kết nối demo" subtitle="Nút này chỉ lưu trạng thái preview để trình bày flow tích hợp, không lưu token nhạy cảm.">
          <label className="block">
            <span className="text-sm text-[color:var(--text-muted)]">Tên hiển thị</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} className="mt-2 w-full rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none" />
          </label>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={async () => setStatus(await connectSpotifyPreview({ display_name: displayName, scopes: ["user-read-email"] }))} className="btn-primary rounded-lg px-5 py-3 text-sm font-semibold transition">Kết nối preview</button>
            <button type="button" onClick={async () => setStatus(await disconnectSpotify())} className="btn-secondary rounded-lg px-5 py-3 text-sm font-semibold transition">Ngắt kết nối</button>
          </div>
        </AppCard>
      </div>
    </AppShell>
  );
}
