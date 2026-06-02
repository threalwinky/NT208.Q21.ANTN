"use client";

import Link from "next/link";
import { ArrowRight, BellDot, CalendarRange, MessageCircleHeart, NotebookPen } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { readAuth } from "@/lib/auth";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const auth = readAuth();
    if (auth) {
      router.replace(auth.user.role === "ADMIN" ? "/admin" : "/dashboard");
    }
  }, [router]);

  return (
    <main className="min-h-screen overflow-hidden px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-[1380px] flex-col rounded-[32px] border border-[color:var(--line)] bg-[color:var(--surface)] shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--line)] px-6 py-5 lg:px-8">
          <div>
            <p className="text-sm font-semibold text-[color:var(--accent)]">Studify</p>
            <p className="mt-1 text-sm text-[color:var(--text-muted)]">Không gian hỗ trợ sinh viên UIT</p>
          </div>
          <Link href="/login" className="btn-primary inline-flex items-center gap-2 rounded-[18px] px-4 py-2.5 text-sm font-semibold transition">
            Đăng nhập
            <ArrowRight className="h-4 w-4" />
          </Link>
        </header>

        <section className="flex flex-1 flex-col items-center justify-center gap-10 px-6 py-10 text-center lg:px-8 lg:py-12">
          <div className="max-w-4xl">
            <div className="inline-flex rounded-full bg-[color:var(--accent-soft)] px-3 py-1 text-sm font-medium text-[color:var(--accent)]">
              Dành cho sinh viên đang học
            </div>
            <h1 className="mt-6 text-5xl font-semibold leading-none tracking-tight sm:text-7xl">Studify</h1>
            <p className="mt-5 text-base leading-8 text-[color:var(--text-muted)] sm:text-lg">
              Học tập tận tâm tận tình cho sinh viên UIT
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link href="/login" className="btn-primary inline-flex items-center gap-2 rounded-[18px] px-5 py-3 text-sm font-semibold transition">
                Vào Studify
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          <div className="grid w-full max-w-4xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { title: "Chat", subtitle: "Hỏi học vụ hoặc nhờ gỡ rối nhanh.", icon: MessageCircleHeart },
              { title: "Thông báo", subtitle: "Theo dõi tin mới từ các nguồn UIT.", icon: BellDot },
              { title: "Lịch", subtitle: "Xem việc cần làm, deadline và nhắc việc.", icon: CalendarRange },
              { title: "Nhật ký", subtitle: "Ghi ngắn tâm trạng và nghe một bài cho dễ thở hơn.", icon: NotebookPen },
            ].map((item) => (
              <div key={item.title} className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5">
                <item.icon className="h-5 w-5 text-[color:var(--accent)]" />
                <p className="mt-4 text-lg font-semibold">{item.title}</p>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{item.subtitle}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
