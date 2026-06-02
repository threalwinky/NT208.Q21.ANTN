"use client";

import Link from "next/link";
import { ArrowRight, KeyRound, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { login } from "@/lib/api";
import { saveAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await login(username, password);
      saveAuth({ token: result.access_token, user: result.user });
      router.push(result.user.role === "ADMIN" ? "/admin" : "/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Không thể đăng nhập.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1280px] items-center gap-6 rounded-[28px] border border-[color:var(--line)] bg-[color:var(--surface)] p-6 shadow-[0_18px_60px_rgba(15,23,42,0.06)] lg:grid-cols-[0.95fr_1.05fr] lg:p-8">
        <section className="rounded-[24px] bg-[color:var(--surface-soft)] p-8">
          <p className="text-sm font-semibold text-[color:var(--accent)]">Studify</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">Đăng nhập</h1>
          <p className="mt-3 max-w-lg text-sm leading-7 text-[color:var(--text-muted)]">
            Dùng mã số sinh viên và mật khẩu để vào dashboard, lịch học, thông báo và chat.
          </p>

          <div className="mt-8 grid gap-3">
            {["Thông báo UIT", "Học vụ", "Lịch và việc cần làm", "Chat hỗ trợ"].map((item) => (
              <div key={item} className="rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3 text-sm">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block space-y-2">
              <span className="text-sm font-medium">Mã số sinh viên</span>
              <div className="relative">
                <UserRound className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--text-soft)]" />
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] py-3 pl-11 pr-4 outline-none transition focus:border-[color:var(--accent)]"
                  placeholder="Ví dụ: 24522045"
                />
              </div>
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium">Mật khẩu</span>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--text-soft)]" />
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] py-3 pl-11 pr-4 outline-none transition focus:border-[color:var(--accent)]"
                  placeholder="Nhập mật khẩu"
                />
              </div>
            </label>

            {error ? (
              <p className="rounded-[18px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary inline-flex w-full items-center justify-center gap-2 rounded-[18px] px-5 py-3 text-sm font-semibold transition disabled:opacity-60"
            >
              {loading ? "Đang đăng nhập..." : "Vào Studify"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <Link href="/" className="mt-5 inline-flex text-sm text-[color:var(--text-muted)] transition hover:text-[color:var(--text-primary)]">
            Quay lại trang chủ
          </Link>
        </section>
      </div>
    </main>
  );
}
