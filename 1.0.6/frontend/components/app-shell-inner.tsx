"use client";

import Link from "next/link";
import {
  Bell,
  Bot,
  BookOpen,
  CalendarDays,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  NotebookPen,
  Search,
  Settings2,
  TrendingUp,
  X,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { logout as logoutApi } from "@/lib/api";
import { clearAuth, loadTheme, readAuth } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Bảng điều khiển", icon: LayoutDashboard },
  { href: "/assistant", label: "Chat", icon: Bot },
  { href: "/revision", label: "Ôn tập", icon: BookOpen },
  { href: "/advisor", label: "Học tập", icon: GraduationCap },
  { href: "/gpa", label: "GPA", icon: TrendingUp },
  { href: "/planner", label: "Lịch", icon: CalendarDays },
  { href: "/announcements", label: "Thông báo", icon: Bell },
  { href: "/search", label: "Tìm kiếm", icon: Search },
  { href: "/diary", label: "Nhật ký", icon: NotebookPen },
  { href: "/admin", label: "Quản trị", icon: Settings2, adminOnly: true },
];

export function AppShellInner({
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
  const [auth, setAuth] = useState<ReturnType<typeof readAuth>>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    loadTheme();
    const currentAuth = readAuth();
    if (!currentAuth) {
      router.replace("/login");
      return;
    }
    queueMicrotask(() => setAuth(currentAuth));
  }, [router]);

  async function handleLogout() {
    await logoutApi().catch(() => null);
    clearAuth();
    router.replace("/login");
  }

  const isAdmin = auth?.user.role === "ADMIN";
  const isAssistantVariant = variant === "assistant";

  return (
    <div className={isAssistantVariant ? "h-screen text-[color:var(--text-primary)]" : "min-h-screen text-[color:var(--text-primary)]"}>
      <button
        type="button"
        onClick={() => setSidebarOpen((value) => !value)}
        className="fixed left-4 top-4 z-50 inline-flex h-10 w-10 items-center justify-center rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] text-[color:var(--text-muted)] shadow-sm transition hover:text-[color:var(--text-primary)] lg:hidden"
        aria-label="Mở menu"
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {sidebarOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          aria-label="Đóng menu"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}

      <div
        className={
          isAssistantVariant
            ? "grid h-screen w-full lg:grid-cols-[16rem_minmax(0,1fr)]"
            : "grid min-h-screen w-full lg:grid-cols-[16rem_minmax(0,1fr)]"
        }
      >
        <aside
          className={`fixed left-0 top-0 z-40 flex h-screen w-64 min-h-0 flex-col border-r border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-4 transition-transform duration-300 lg:static lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <Link
            href="/"
            onClick={() => setSidebarOpen(false)}
            className="flex items-center gap-3 border-b border-[color:var(--line)] px-2 pb-5 pt-1"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[color:var(--accent)] text-sm font-semibold text-white">
              S
            </div>
            <div>
              <p className="text-xl font-bold">Studify</p>
              <p className="text-xs text-[color:var(--text-muted)]">Sinh viên UIT</p>
            </div>
          </Link>

          <nav className="mt-4 flex-1 space-y-1 overflow-y-auto pr-1">
            {navItems
              .filter((item) => (item.adminOnly ? isAdmin : true))
              .map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={`group relative flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ease-out ${
                      active
                        ? "bg-[color:var(--accent)] text-white shadow-[0_6px_16px_-4px_rgba(37,99,235,0.5)]"
                        : "text-[color:var(--text-muted)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent)]"
                    }`}
                  >
                    {/* vạch chỉ báo trang đang mở */}
                    <span
                      className={`absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-white transition-all duration-200 ${
                        active ? "opacity-90" : "opacity-0"
                      }`}
                    />
                    <Icon
                      className={`h-5 w-5 shrink-0 transition-transform duration-200 ease-out ${
                        active ? "" : "group-hover:scale-110"
                      }`}
                    />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
          </nav>

          {sidebarExtra ? (
            <div className="mt-4 min-h-0 flex-1 overflow-y-auto border-t border-[color:var(--line)] pt-4">{sidebarExtra}</div>
          ) : null}

          {hideHeader ? (
            <div className="mt-4 border-t border-[color:var(--line)] pt-4">
              <div className="mb-3 inline-flex min-h-12 w-full items-center rounded-md bg-[color:var(--surface-soft)] px-4 py-2">
                <div>
                  <p className="text-sm font-medium leading-tight">{auth?.user.full_name ?? ""}</p>
                  <p className="text-xs leading-tight text-[color:var(--text-muted)]">
                    {auth?.user.student_id ? `MSSV ${auth.user.student_id}` : "Quản trị hệ thống"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <button
                  type="button"
                  onClick={() => void handleLogout()}
                  className="btn-secondary inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition"
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
            <header className="sticky top-0 z-20 border-b border-[color:var(--line)] bg-[color:var(--surface)] px-5 py-4 pl-16 md:px-7 md:pl-16 lg:pl-7 xl:px-10">
              <div className="mx-auto flex w-full max-w-[1320px] flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">{pageTitle}</h1>
                  {pageDescription ? <p className="mt-1 text-sm text-[color:var(--text-muted)]">{pageDescription}</p> : null}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <ThemeToggle />
                  <div className="inline-flex min-h-11 min-w-[172px] items-center rounded-md border border-[color:var(--line)] bg-[color:var(--button-secondary-bg)] px-4 py-2">
                    <div>
                      <p className="text-sm font-medium leading-tight">{auth?.user.full_name ?? ""}</p>
                      <p className="text-xs leading-tight text-[color:var(--text-muted)]">
                        {auth?.user.student_id ? `MSSV ${auth.user.student_id}` : "Quản trị hệ thống"}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleLogout()}
                    className="btn-secondary inline-flex h-11 items-center gap-2 rounded-md px-4 text-sm font-medium transition"
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
              <div className="mx-auto flex w-full max-w-[1320px] flex-col gap-6">{children}</div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
