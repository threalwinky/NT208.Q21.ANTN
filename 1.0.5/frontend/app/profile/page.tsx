"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { getProfile, updateProfile, type Profile } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<Partial<Profile>>({});
  const [message, setMessage] = useState("");

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
    setMessage("Đã lưu hồ sơ.");
  }

  const fields: Array<[keyof Profile, string]> = [
    ["full_name", "Họ tên"],
    ["email", "Email"],
    ["student_id", "MSSV"],
    ["faculty", "Khoa"],
    ["major", "Ngành"],
    ["class_name", "Lớp"],
    ["cohort", "Khóa"],
    ["advisor_name", "Cố vấn học tập"],
  ];

  return (
    <AppShell pageTitle="Hồ sơ cá nhân" pageDescription="Thông tin sinh viên dùng cho cố vấn học vụ, GPA và gợi ý học kỳ.">
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
            {message ? <p className="rounded-2xl bg-[color:var(--accent-soft)] px-4 py-3 text-sm text-[color:var(--accent)]">{message}</p> : null}
          </div>
        </AppCard>

        <AppCard title="Cập nhật hồ sơ" subtitle="Các trường học vụ có thể chỉnh để demo đúng ngành/lớp của sinh viên.">
          <div className="grid gap-3 md:grid-cols-2">
            {fields.map(([key, label]) => (
              <label key={key} className="block">
                <span className="text-sm text-[color:var(--text-muted)]">{label}</span>
                <input
                  value={String(form[key] ?? "")}
                  onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
                  className="mt-2 w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
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
