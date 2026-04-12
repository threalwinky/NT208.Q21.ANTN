"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  BookOpenText,
  Bot,
  CalendarDays,
  GraduationCap,
  HeartHandshake,
  LayoutDashboard,
  LogOut,
  Settings2,
} from "lucide-react";
import { useEffect } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { clearAuth, loadTheme, readAuth } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Bảng điều khiển", icon: LayoutDashboard },
  { href: "/assistant", label: "Chat", icon: Bot },
  { href: "/academic", label: "Học vụ", icon: BookOpenText },
  { href: "/advisor", label: "Cố vấn", icon: GraduationCap },
  { href: "/planner", label: "Lịch", icon: CalendarDays },
  { href: "/announcements", label: "Thông báo", icon: Bell },
  { href: "/diary", label: "Nhật ký", icon: HeartHandshake },
  { href: "/admin", label: "Quản trị", icon: Settings2, adminOnly: true },
];

export function AppShell({
  children,
  pageTitle,
  pageDescription,
  hideHeader = false,
  sidebarExtra,
  variant = "default",
}: {
  children: React.ReactNode;
  pageTitle: string;
  pageDescription?: string;
  hideHeader?: boolean;
  sidebarExtra?: React.ReactNode;
  variant?: "default" | "assistant";
}) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = typeof window === "undefined" ? null : readAuth();

  useEffect(() => {
    loadTheme();
    if (!readAuth()) {
      router.push("/login");
    }
  }, [pathname, router]);

  if (!auth) {
    return null;
  }

  const isAdmin = auth.user.role === "ADMIN";
  const isAssistantVariant = variant === "assistant";
  const isDefaultVariant = variant === "default";

  return (
    <div className={isAssistantVariant ? "h-screen text-[color:var(--text-primary)]" : "min-h-screen text-[color:var(--text-primary)]"}>
      <div
        className={
          isAssistantVariant
            ? "grid h-screen w-full lg:grid-cols-[280px_minmax(0,1fr)]"
            : "grid min-h-screen w-full lg:grid-cols-[280px_minmax(0,1fr)]"
        }
      >
        <aside
          className={
            isAssistantVariant || isDefaultVariant
              ? "flex min-h-0 flex-col border-r border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-4"
              : "flex min-h-0 flex-col rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-4 shadow-[0_10px_30px_rgba(15,23,42,0.05)]"
          }
        >
          <Link
            href="/"
            className={
              isAssistantVariant
                ? "flex items-center gap-3 rounded-[18px] bg-[color:var(--surface-soft)] px-4 py-4"
                : "flex items-center gap-3 rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-4"
            }
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[color:var(--accent)] text-sm font-semibold text-white">
              S
            </div>
            <div>
              <p className="text-sm font-semibold">Studify</p>
              <p className="text-xs text-[color:var(--text-muted)]">Sinh viên UIT</p>
            </div>
          </Link>

          <nav className="mt-4 space-y-1.5">
            {navItems
              .filter((item) => (item.adminOnly ? isAdmin : true))
              .map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 rounded-[18px] px-4 py-3 text-sm transition ${
                      active
                        ? "bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                        : "text-[color:var(--text-muted)] hover:bg-[color:var(--surface-soft)] hover:text-[color:var(--text-primary)]"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
          </nav>

          {sidebarExtra ? (
            <div className="mt-4 min-h-0 flex-1 overflow-y-auto border-t border-[color:var(--line)] pt-4">{sidebarExtra}</div>
          ) : null}

          {hideHeader ? (
            <div className="mt-4 border-t border-[color:var(--line)] pt-4">
              <div className="mb-3 inline-flex h-12 w-full items-center rounded-[18px] border border-[color:var(--line)] bg-[color:var(--button-secondary-bg)] px-4">
                <div>
                  <p className="text-sm font-medium leading-tight">{auth.user.full_name}</p>
                  <p className="text-xs leading-tight text-[color:var(--text-muted)]">
                    {auth.user.student_id ? `MSSV ${auth.user.student_id}` : "Quản trị hệ thống"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <button
                  type="button"
                  onClick={() => {
                    clearAuth();
                    router.push("/login");
                  }}
                  className="btn-secondary inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-[18px] px-4 text-sm font-medium transition"
                >
                  <LogOut className="h-4 w-4" />
                  Đăng xuất
                </button>
              </div>
            </div>
          ) : null}
        </aside>

        <main className={isAssistantVariant ? "flex min-h-0 flex-col overflow-hidden bg-[color:var(--page-bg)]" : "flex min-h-screen flex-col overflow-x-hidden bg-[color:var(--page-bg)]"}>
          {!hideHeader ? (
            <header className="border-b border-[color:var(--line)] bg-[color:var(--surface)] px-5 py-5 md:px-7 xl:px-10">
              <div className="mx-auto flex w-full max-w-[1320px] flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">{pageTitle}</h1>
                  {pageDescription ? <p className="mt-1 text-sm text-[color:var(--text-muted)]">{pageDescription}</p> : null}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <ThemeToggle />
                  <div className="inline-flex h-12 min-w-[172px] items-center rounded-[18px] border border-[color:var(--line)] bg-[color:var(--button-secondary-bg)] px-4">
                    <div>
                      <p className="text-sm font-medium leading-tight">{auth.user.full_name}</p>
                      <p className="text-xs leading-tight text-[color:var(--text-muted)]">
                        {auth.user.student_id ? `MSSV ${auth.user.student_id}` : "Quản trị hệ thống"}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      clearAuth();
                      router.push("/login");
                    }}
                    className="btn-secondary inline-flex h-12 items-center gap-2 rounded-[18px] px-4 text-sm font-medium transition"
                  >
                    <LogOut className="h-4 w-4" />
                    Đăng xuất
                  </button>
                </div>
              </div>
            </header>
          ) : null}
          {isAssistantVariant ? (
            children
          ) : (
            <div className="flex-1 px-5 py-6 md:px-7 xl:px-10">
              <div className="mx-auto flex w-full max-w-[1320px] flex-col gap-8">{children}</div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
