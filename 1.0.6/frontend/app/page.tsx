"use client";

import Link from "next/link";
import {
  ArrowRight,
  BellDot,
  CalendarRange,
  GraduationCap,
  MessageCircleHeart,
  Quote,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { readAuth } from "@/lib/auth";

const FEATURES = [
  {
    icon: GraduationCap,
    title: "Cố vấn học vụ",
    desc: "Hỏi lịch thi, học phí, tốt nghiệp, đăng ký học phần — trả lời gọn và kèm trích dẫn nguồn UIT.",
  },
  {
    icon: BellDot,
    title: "Thông báo UIT",
    desc: "Tổng hợp thông báo từ các cổng của trường, gom nhóm theo học vụ, CTSV, học bổng, học phí.",
  },
  {
    icon: CalendarRange,
    title: "Lịch & deadline",
    desc: "Quản lý việc cần làm, deadline đồ án, nhắc lịch thi và đăng ký học phần ở một nơi.",
  },
  {
    icon: MessageCircleHeart,
    title: "Đồng hành tinh thần",
    desc: "Lắng nghe khi bạn căng thẳng, gợi ý nghỉ ngắn và hướng tới hỗ trợ thật khi cần.",
  },
];

const HIGHLIGHTS = [
  { icon: ShieldCheck, title: "Ưu tiên nguồn chính thức", desc: "Câu trả lời học vụ bám theo dữ liệu công bố từ các cổng UIT." },
  { icon: Quote, title: "Luôn kèm trích dẫn", desc: "Mỗi thông tin học vụ đều dẫn lại nguồn để bạn kiểm chứng." },
  { icon: Sparkles, title: "An toàn khi tâm sự", desc: "Phát hiện tín hiệu nguy cơ và chuyển hướng tới hỗ trợ con người." },
];

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const auth = readAuth();
    if (auth) {
      router.replace(auth.user.role === "ADMIN" ? "/admin" : "/dashboard");
    }
  }, [router]);

  return (
    <main className="min-h-screen bg-[color:var(--page-bg)]">
      {/* ── Thanh điều hướng ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-[color:var(--line)] bg-[color:var(--surface)]/85 backdrop-blur">
        <div className="studify-container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[color:var(--accent)] text-sm font-bold text-white">
              S
            </span>
            <span className="text-base font-semibold tracking-tight">Studify</span>
          </Link>

          <nav className="hidden items-center gap-8 text-sm text-[color:var(--text-muted)] md:flex">
            <a href="#tinh-nang" className="transition hover:text-[color:var(--text-primary)]">Tính năng</a>
            <a href="#vi-sao" className="transition hover:text-[color:var(--text-primary)]">Vì sao Studify</a>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="hidden rounded-lg px-4 py-2 text-sm font-medium text-[color:var(--text-muted)] transition hover:text-[color:var(--text-primary)] sm:inline-flex"
            >
              Đăng nhập
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 rounded-lg bg-[color:var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[color:var(--accent-strong)]"
            >
              Vào Studify
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* vầng sáng xanh dịu phía sau */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-[-6rem] h-[26rem] w-[40rem] -translate-x-1/2 rounded-full opacity-60 blur-[120px]"
          style={{ background: "radial-gradient(circle, rgba(37,99,235,0.18), transparent 70%)" }}
        />
        <div className="studify-container relative py-20 text-center sm:py-28">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--surface)] px-3.5 py-1.5 text-sm text-[color:var(--text-muted)] shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--accent)]" />
            Người bạn đồng hành của sinh viên UIT
          </div>

          <h1 className="mx-auto mt-7 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            Học nhẹ nhàng hơn với{" "}
            <span className="bg-gradient-to-r from-[#2563eb] to-[#60a5fa] bg-clip-text text-transparent">Studify</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-[color:var(--text-muted)] sm:text-lg">
            Một nơi để tra cứu học vụ, theo dõi thông báo, quản lý deadline và trò chuyện khi bạn cần —
            tất cả dựa trên dữ liệu chính thức của Trường Đại học Công nghệ Thông tin.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-xl bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[color:var(--accent-strong)]"
            >
              Bắt đầu ngay
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#tinh-nang"
              className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--line)] bg-[color:var(--surface)] px-6 py-3 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[color:var(--surface-soft)]"
            >
              Tìm hiểu thêm
            </a>
          </div>
        </div>
      </section>

      {/* ── Tính năng ────────────────────────────────────────────────────── */}
      <section id="tinh-nang" className="studify-container py-16 sm:py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Mọi việc của sinh viên, gọn trong một nơi</h2>
          <p className="mt-4 text-base leading-7 text-[color:var(--text-muted)]">
            Studify gom những việc bạn làm mỗi ngày thành các khu vực rõ ràng, dễ dùng.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((item) => (
            <div key={item.title} className="card-soft p-6 transition hover:shadow-[var(--shadow-card-hover)]">
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                <item.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-5 text-lg font-semibold tracking-tight">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Vì sao Studify ───────────────────────────────────────────────── */}
      <section id="vi-sao" className="border-y border-[color:var(--line)] bg-[color:var(--surface)]">
        <div className="studify-container py-16 sm:py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Đáng tin và an toàn</h2>
            <p className="mt-4 text-base leading-7 text-[color:var(--text-muted)]">
              Studify ưu tiên thông tin chính thức và giữ ranh giới an toàn khi bạn cần tâm sự.
            </p>
          </div>

          <div className="mx-auto mt-12 grid max-w-4xl gap-10 sm:grid-cols-3">
            {HIGHLIGHTS.map((item) => (
              <div key={item.title} className="text-center sm:text-left">
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <item.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-5 text-base font-semibold tracking-tight">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="studify-container py-16 sm:py-20">
        <div className="relative overflow-hidden rounded-3xl bg-[color:var(--accent)] px-8 py-14 text-center text-white sm:px-16">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{ background: "radial-gradient(circle at 30% 20%, rgba(255,255,255,0.35), transparent 55%)" }}
          />
          <div className="relative">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Sẵn sàng học nhẹ nhàng hơn?</h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-white/85">
              Đăng nhập bằng tài khoản sinh viên UIT để bắt đầu cùng Studify.
            </p>
            <Link
              href="/login"
              className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-[color:var(--accent)] shadow-sm transition hover:bg-white/90"
            >
              Vào Studify
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-[color:var(--line)]">
        <div className="studify-container flex flex-col gap-6 py-10 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-md">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--accent)] text-xs font-bold text-white">
                S
              </span>
              <span className="text-sm font-semibold">Studify</span>
            </div>
            <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
              Sản phẩm đồ án hỗ trợ sinh viên UIT. Thông tin học vụ chính thức luôn theo công bố của nhà trường;
              phần đồng hành tinh thần chỉ ở mức hỗ trợ ban đầu, không thay thế chuyên gia.
            </p>
          </div>
          <p className="text-sm text-[color:var(--text-soft)]">© {new Date().getFullYear()} Studify · Sinh viên UIT</p>
        </div>
      </footer>
    </main>
  );
}
