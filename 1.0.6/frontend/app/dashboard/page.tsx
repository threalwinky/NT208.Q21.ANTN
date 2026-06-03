"use client";

import {
  ArrowRight,
  Bell,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Clock3,
  GraduationCap,
  HeartPulse,
  LayoutDashboard,
  Sparkle,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { getDashboardOverview } from "@/lib/api";
import { formatDate, formatDateTime, formatDeadlineDistance } from "@/lib/format";

type DashboardData = Awaited<ReturnType<typeof getDashboardOverview>>;
type AnnouncementItem = DashboardData["announcements"][number];
type TaskItem = DashboardData["upcoming_tasks"][number];
type ScheduleItem = DashboardData["today_schedule"][number];
type TabKey = "tong-quan" | "hoc-tap" | "thong-bao" | "deadline" | "lich";

const DASHBOARD_TABS: Array<{
  id: TabKey;
  label: string;
  description: string;
  icon: typeof LayoutDashboard;
}> = [
  { id: "tong-quan", label: "Tổng quan", description: "Việc cần chú ý", icon: LayoutDashboard },
  { id: "hoc-tap", label: "Học tập", description: "Tiến độ và rủi ro", icon: GraduationCap },
  { id: "thong-bao", label: "Thông báo", description: "Tin UIT mới", icon: Bell },
  { id: "deadline", label: "Deadline", description: "Việc gần hạn", icon: ClipboardList },
  { id: "lich", label: "Lịch hôm nay", description: "Lịch học và thi", icon: CalendarDays },
];

function sortTasksByDueDate<T extends { due_at?: string | null }>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftTime = left.due_at ? new Date(left.due_at).getTime() : Number.POSITIVE_INFINITY;
    const rightTime = right.due_at ? new Date(right.due_at).getTime() : Number.POSITIVE_INFINITY;
    return leftTime - rightTime;
  });
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function getEnergyTrendCopy(trend?: string | null) {
  if (trend === "DOWN") {
    return "Nhịp đang chùng xuống vài hôm gần đây. Bạn nên giảm tải một chút và ưu tiên việc ngắn trước.";
  }
  if (trend === "UP") {
    return "Nhịp đang đi lên. Đây là lúc tốt để chốt một việc quan trọng đang treo.";
  }
  return "Nhịp đang khá ổn định. Giữ đều các block học ngắn sẽ hợp hơn là dồn quá sâu.";
}

function getRiskTone(value: string): "success" | "warn" | "danger" | "default" {
  const normalized = value.toLowerCase();
  if (normalized.includes("high") || normalized.includes("cao")) return "danger";
  if (normalized.includes("medium") || normalized.includes("trung")) return "warn";
  if (normalized.includes("low") || normalized.includes("thấp")) return "success";
  return "default";
}

function getPriorityTone(value: string): "default" | "accent" | "warn" | "danger" {
  const normalized = value.toLowerCase();
  if (normalized.includes("urgent") || normalized.includes("critical") || normalized.includes("cao")) return "danger";
  if (normalized.includes("high")) return "warn";
  if (normalized.includes("medium") || normalized.includes("vừa")) return "accent";
  return "default";
}

function EmptyState({ children }: { children: string }) {
  return (
    <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-8 text-center text-sm text-[color:var(--text-muted)]">
      {children}
    </div>
  );
}

function MetricTile({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: typeof LayoutDashboard;
}) {
  return (
    <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-[color:var(--text-muted)]">{label}</p>
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-4 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)]">{value}</p>
      <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[color:var(--text-soft)]">{hint}</p>
    </div>
  );
}

function TabNavigation({ activeTab, onChange }: { activeTab: TabKey; onChange: (tab: TabKey) => void }) {
  return (
    <div
      role="tablist"
      aria-label="Nhóm nội dung bảng điều khiển"
      className="grid gap-2 rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-2 md:grid-cols-3 xl:grid-cols-5"
    >
      {DASHBOARD_TABS.map((tab) => {
        const Icon = tab.icon;
        const selected = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            id={`dashboard-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`dashboard-panel-${tab.id}`}
            onClick={() => onChange(tab.id)}
            className={[
              "flex min-h-16 items-center gap-3 rounded-md border px-4 py-3 text-left text-sm transition",
              selected
                ? "border-[color:var(--accent)] bg-[color:var(--accent)] text-white shadow-sm"
                : "border-transparent bg-[color:var(--surface)] text-[color:var(--text-muted)] hover:border-[color:var(--line)] hover:text-[color:var(--text-primary)]",
            ].join(" ")}
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span className="min-w-0">
              <span className="block font-semibold">{tab.label}</span>
              <span className={`mt-0.5 hidden text-xs sm:block ${selected ? "text-white/75" : "text-[color:var(--text-soft)]"}`}>
                {tab.description}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function EnergyInsight({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
        <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
          <Sparkle className="h-4 w-4 text-[color:var(--accent)]" />
          Năng lượng hiện tại
        </div>
        <p className="mt-3 text-lg font-semibold text-[color:var(--text-primary)]">
          {loading && !data
            ? "Đang tải nhịp gần nhất..."
            : `${data?.mood_label ?? "Chưa có tâm trạng gần nhất"} • mức ${data?.latest_energy_level ?? 3}/5`}
        </p>
        <p className="mt-2 text-sm leading-6 text-[color:var(--text-primary)]">
          {data?.energy_summary ?? "Khi có check-in mới, Studify sẽ tóm tắt nhịp năng lượng tại đây."}
        </p>
      </div>

      <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
        <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
          <Zap className="h-4 w-4 text-[color:var(--accent)]" />
          Xu hướng
        </div>
        <p className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">{getEnergyTrendCopy(data?.energy_trend)}</p>
      </div>
    </div>
  );
}

function AnnouncementList({ items, loading, limit }: { items: AnnouncementItem[]; loading: boolean; limit?: number }) {
  const visibleItems = typeof limit === "number" ? items.slice(0, limit) : items;

  if (visibleItems.length === 0) {
    return <EmptyState>{loading ? "Đang tải thông báo mới..." : "Chưa có thông báo mới để hiển thị."}</EmptyState>;
  }

  return (
    <div className="space-y-3">
      {visibleItems.map((item) => (
        <a
          key={item.id}
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="block rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="font-semibold leading-6 text-[color:var(--text-primary)]">{item.title}</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                {item.group_name} • {formatDate(item.published_at)}
              </p>
            </div>
            <Badge tone="default">{item.group_name}</Badge>
          </div>
        </a>
      ))}
    </div>
  );
}

function DeadlineList({ items, loading, limit }: { items: TaskItem[]; loading: boolean; limit?: number }) {
  const visibleItems = typeof limit === "number" ? items.slice(0, limit) : items;

  if (visibleItems.length === 0) {
    return <EmptyState>{loading ? "Đang tải deadline..." : "Chưa có việc gần hạn."}</EmptyState>;
  }

  return (
    <div className="space-y-3">
      {visibleItems.map((task) => (
        <div key={task.id} className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="font-semibold text-[color:var(--text-primary)]">{task.title}</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                {task.task_type} • {task.status}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 sm:justify-end">
              <Badge tone={task.due_at ? "accent" : "default"}>{formatDeadlineDistance(task.due_at)}</Badge>
              <Badge tone={getPriorityTone(task.priority)}>{task.priority}</Badge>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[color:var(--text-soft)]">
            <Clock3 className="h-4 w-4" />
            {formatDateTime(task.due_at)}
          </div>
        </div>
      ))}
    </div>
  );
}

function ScheduleList({ items, loading, limit }: { items: ScheduleItem[]; loading: boolean; limit?: number }) {
  const visibleItems = typeof limit === "number" ? items.slice(0, limit) : items;

  if (visibleItems.length === 0) {
    return <EmptyState>{loading ? "Đang tải lịch hôm nay..." : "Hôm nay chưa có lịch học hoặc lịch thi."}</EmptyState>;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {visibleItems.map((item) => (
        <div key={`${item.title}-${item.starts_at}`} className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
          <Badge tone={item.item_type === "LỊCH THI" ? "warn" : "accent"}>{item.item_type}</Badge>
          <p className="mt-4 font-semibold text-[color:var(--text-primary)]">{item.title}</p>
          <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.location ?? "Chưa có phòng"}</p>
          <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(item.starts_at)}</p>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("tong-quan");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError("");
        const payload = await getDashboardOverview();
        if (!mounted) {
          return;
        }
        setData({
          ...payload,
          upcoming_tasks: sortTasksByDueDate(payload.upcoming_tasks),
        });
      } catch (caughtError) {
        if (mounted) {
          setError(caughtError instanceof Error ? caughtError.message : "Không tải được dữ liệu bảng điều khiển.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  const announcements = data?.announcements ?? [];
  const upcomingTasks = data?.upcoming_tasks ?? [];
  const todaySchedule = data?.today_schedule ?? [];
  const metrics = data?.metrics ?? {};
  const advisorSummary = data?.advisor_summary ?? {};
  const completionPercent = clampPercent(Number(advisorSummary.completionPercent ?? 0));
  const riskLevel = String(advisorSummary.riskLevel ?? "LOW");
  const riskScore = Number(advisorSummary.riskScore ?? 0);
  const nextSemesterCredits = Number(advisorSummary.nextSemesterCredits ?? 0);
  const blockingCourses = Number(advisorSummary.blockingCourses ?? 0);

  return (
    <AppShell
      pageTitle="Bảng điều khiển sinh viên"
      pageDescription="Theo dõi nhanh những việc quan trọng theo từng tab: học tập, thông báo, deadline, lịch và nhịp cảm xúc."
    >
      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricTile
              label="Thông báo"
              value={loading && !data ? "..." : `${metrics.totalAnnouncements ?? 0}`}
              hint="Nguồn UIT"
              icon={Bell}
            />
            <MetricTile
              label="Việc chưa xong"
              value={loading && !data ? "..." : `${metrics.openTasks ?? 0}`}
              hint="Cần xử lý"
              icon={ClipboardList}
            />
            <MetricTile
              label="Lịch thi"
              value={loading && !data ? "..." : `${metrics.upcomingExams ?? 0}`}
              hint="Sắp tới"
              icon={CalendarDays}
            />
            <MetricTile
              label="Nhật ký"
              value={loading && !data ? "..." : `${metrics.moodCheckins ?? 0}`}
              hint="Tuần này"
              icon={HeartPulse}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Link
              href="/announcements"
              className="group rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:border-[color:var(--accent)] hover:shadow-[var(--shadow-card-hover)]"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <Bell className="h-4 w-4" />
                </span>
                <ArrowRight className="h-4 w-4 text-[color:var(--text-soft)] transition group-hover:translate-x-1 group-hover:text-[color:var(--accent)]" />
              </div>
              <p className="mt-4 font-semibold text-[color:var(--text-primary)]">Đọc thông báo mới</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">{announcements.length} thông báo đang được ưu tiên.</p>
            </Link>

            <Link
              href="/planner"
              className="group rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:border-[color:var(--accent)] hover:shadow-[var(--shadow-card-hover)]"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <Clock3 className="h-4 w-4" />
                </span>
                <ArrowRight className="h-4 w-4 text-[color:var(--text-soft)] transition group-hover:translate-x-1 group-hover:text-[color:var(--accent)]" />
              </div>
              <p className="mt-4 font-semibold text-[color:var(--text-primary)]">Chốt việc gần hạn</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">{upcomingTasks.length} việc được sắp theo hạn gần nhất.</p>
            </Link>

            <Link
              href="/diary"
              className="group rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:border-[color:var(--accent)] hover:shadow-[var(--shadow-card-hover)]"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <HeartPulse className="h-4 w-4" />
                </span>
                <ArrowRight className="h-4 w-4 text-[color:var(--text-soft)] transition group-hover:translate-x-1 group-hover:text-[color:var(--accent)]" />
              </div>
              <p className="mt-4 font-semibold text-[color:var(--text-primary)]">Check-in cảm xúc</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">Cập nhật nhịp học và năng lượng hôm nay.</p>
            </Link>
          </div>
        </div>

        <AppCard
          title="Nhịp hôm nay"
          subtitle="Tóm tắt nhanh từ check-in và nhật ký gần nhất."
          action={<Badge tone="accent">{data?.latest_energy_label ?? "Trung bình"}</Badge>}
        >
          <EnergyInsight data={data} loading={loading} />
        </AppCard>
      </section>

      <TabNavigation activeTab={activeTab} onChange={setActiveTab} />

      <div
        id={`dashboard-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`dashboard-tab-${activeTab}`}
        className="space-y-4"
      >
        {activeTab === "tong-quan" ? (
          <div className="grid gap-4 xl:grid-cols-2">
            <AppCard
              title="Việc cần ưu tiên"
              subtitle="Ba deadline gần nhất để bạn xử lý trước."
              action={
                <Link href="/planner" className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]">
                  Mở lịch
                </Link>
              }
            >
              <DeadlineList items={upcomingTasks} loading={loading} limit={3} />
            </AppCard>

            <AppCard
              title="Thông báo nên đọc"
              subtitle="Các thông báo mới nhất từ nguồn UIT."
              action={
                <Link href="/announcements" className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]">
                  Xem tất cả
                </Link>
              }
            >
              <AnnouncementList items={announcements} loading={loading} limit={3} />
            </AppCard>

            <AppCard
              className="xl:col-span-2"
              title="Lịch hôm nay"
              subtitle="Các mốc học và thi gần nhất trong ngày."
              action={
                <Link href="/planner" className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]">
                  Mở kế hoạch
                </Link>
              }
            >
              <ScheduleList items={todaySchedule} loading={loading} limit={3} />
            </AppCard>
          </div>
        ) : null}

        {activeTab === "hoc-tap" ? (
          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <AppCard
              title="Tiến độ học tập"
              subtitle="Tổng hợp từ degree audit và risk score."
              action={
                <Link
                  href="/advisor"
                  className="inline-flex h-10 items-center rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[color:var(--accent-soft)]"
                >
                  Mở học tập
                </Link>
              }
            >
              <div className="space-y-5">
                <div>
                  <div className="flex items-end justify-between gap-4">
                    <div>
                      <p className="text-sm text-[color:var(--text-muted)]">Tiến độ CTĐT</p>
                      <p className="mt-2 text-4xl font-semibold tracking-tight text-[color:var(--text-primary)]">{completionPercent}%</p>
                    </div>
                    <Badge tone={getRiskTone(riskLevel)}>{riskLevel}</Badge>
                  </div>
                  <div className="mt-4 h-3 overflow-hidden rounded-full bg-[color:var(--surface-soft)]">
                    <div className="h-full rounded-full bg-[color:var(--accent)]" style={{ width: `${completionPercent}%` }} />
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <p className="text-sm text-[color:var(--text-muted)]">Risk score</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{riskScore}</p>
                  </div>
                  <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <p className="text-sm text-[color:var(--text-muted)]">Kỳ tới</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{nextSemesterCredits} TC</p>
                  </div>
                  <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                    <p className="text-sm text-[color:var(--text-muted)]">Môn chặn</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">{blockingCourses}</p>
                  </div>
                </div>
              </div>
            </AppCard>

            <AppCard title="Gợi ý xử lý" subtitle="Các lối tắt phù hợp với trạng thái học tập hiện tại.">
              <div className="grid gap-3 md:grid-cols-2">
                <Link href="/advisor" className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]">
                  <CheckCircle2 className="h-5 w-5 text-[color:var(--accent)]" />
                  <p className="mt-3 font-semibold text-[color:var(--text-primary)]">Kiểm tra môn còn thiếu</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Mở degree audit để xem môn bắt buộc, môn chặn và tín chỉ còn thiếu.</p>
                </Link>
                <Link href="/gpa" className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)]">
                  <GraduationCap className="h-5 w-5 text-[color:var(--accent)]" />
                  <p className="mt-3 font-semibold text-[color:var(--text-primary)]">Tính GPA mục tiêu</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Mô phỏng điểm cần đạt để giữ nhịp học kỳ và giảm rủi ro học tập.</p>
                </Link>
                <Link href="/planner" className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)] md:col-span-2">
                  <CalendarDays className="h-5 w-5 text-[color:var(--accent)]" />
                  <p className="mt-3 font-semibold text-[color:var(--text-primary)]">Sắp lại lịch học tuần này</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">Đưa các deadline gần nhất vào block học ngắn, ưu tiên việc quan trọng trước.</p>
                </Link>
              </div>
            </AppCard>
          </div>
        ) : null}

        {activeTab === "thong-bao" ? (
          <AppCard
            title="Thông báo mới"
            subtitle="Ưu tiên bài mới từ UIT chính thức và các nhóm có ảnh hưởng trực tiếp đến sinh viên."
            action={
              <Link href="/announcements" className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]">
                Mở bảng thông báo
              </Link>
            }
          >
            <AnnouncementList items={announcements} loading={loading} />
          </AppCard>
        ) : null}

        {activeTab === "deadline" ? (
          <AppCard
            title="Deadline gần tới"
            subtitle="Danh sách việc cần làm được kéo lên theo hạn chót gần nhất."
            action={
              <Link href="/planner" className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]">
                Quản lý việc
              </Link>
            }
          >
            <DeadlineList items={upcomingTasks} loading={loading} />
          </AppCard>
        ) : null}

        {activeTab === "lich" ? (
          <AppCard
            title="Lịch hôm nay"
            subtitle="Hiển thị cả lịch học và lịch thi gần nhất để bạn không bị bỏ sót mốc quan trọng."
            action={
              <Link href="/planner" className="text-sm font-semibold text-[color:var(--accent)] hover:text-[color:var(--accent-strong)]">
                Mở lịch đầy đủ
              </Link>
            }
          >
            <ScheduleList items={todaySchedule} loading={loading} />
          </AppCard>
        ) : null}
      </div>
    </AppShell>
  );
}
