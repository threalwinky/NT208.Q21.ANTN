"use client";

import { Clock3, Sparkle, Zap } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge, StatCard } from "@/components/ui";
import { getDashboardOverview } from "@/lib/api";
import { formatDateTime, formatDeadlineDistance } from "@/lib/format";

type DashboardData = Awaited<ReturnType<typeof getDashboardOverview>>;

function sortTasksByDueDate<T extends { due_at?: string | null }>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftTime = left.due_at ? new Date(left.due_at).getTime() : Number.POSITIVE_INFINITY;
    const rightTime = right.due_at ? new Date(right.due_at).getTime() : Number.POSITIVE_INFINITY;
    return leftTime - rightTime;
  });
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
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

  return (
    <AppShell
      pageTitle="Bảng điều khiển sinh viên"
      pageDescription="Một góc nhìn nhanh để bạn nắm thông báo mới, deadline gần đến, lịch học hôm nay và nhịp cảm xúc gần nhất."
    >
      {error ? (
        <div className="mb-4 rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Thông báo đang theo dõi" value={`${data?.metrics.totalAnnouncements ?? 0}`} hint="Tổng hợp từ các nguồn UIT" />
          <StatCard label="Việc chưa xong" value={`${data?.metrics.openTasks ?? 0}`} hint="Task cá nhân + deadline học tập" />
          <StatCard label="Lịch thi sắp tới" value={`${data?.metrics.upcomingExams ?? 0}`} hint="Tự động lấy từ lịch thi" />
          <StatCard label="Nhật ký" value={`${data?.metrics.moodCheckins ?? 0}`} hint="Theo dõi nhịp học tuần này" />
        </section>

        <AppCard
          title="Nhịp hôm nay"
          subtitle="Nhịp năng lượng gần nhất được đọc từ tâm trạng và vài dòng nhật ký của bạn."
          action={<Badge tone="accent">{data?.latest_energy_label ?? "Trung bình"}</Badge>}
        >
          <div className="grid gap-3">
            <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                <Sparkle className="h-4 w-4 text-[color:var(--accent)]" />
                Năng lượng hiện tại
              </div>
              <p className="mt-3 text-lg font-semibold text-[color:var(--text-primary)]">
                {loading ? "Đang tải nhịp gần nhất..." : `${data?.mood_label ?? "Chưa có tâm trạng gần nhất"} • mức ${data?.latest_energy_level ?? 3}/5`}
              </p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-primary)]">{data?.energy_summary}</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                <Zap className="h-4 w-4 text-[color:var(--accent)]" />
                Xu hướng
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">
                {data?.energy_trend === "DOWN"
                  ? "Nhịp đang chùng xuống vài hôm gần đây. Bạn nên giảm tải một chút và ưu tiên việc ngắn trước."
                  : data?.energy_trend === "UP"
                    ? "Nhịp đang đi lên. Đây là lúc tốt để chốt một việc quan trọng đang treo."
                    : "Nhịp đang khá ổn định. Giữ đều các block học ngắn sẽ hợp hơn là dồn quá sâu."}
              </p>
            </div>
          </div>
        </AppCard>
      </div>

      <div>
        <AppCard
          title="Cố vấn học tập"
          subtitle="Tiến độ tốt nghiệp, risk score và tải học kỳ gợi ý được kéo ra từ degree audit mới."
          action={
            <Link
              href="/advisor"
              className="inline-flex h-11 items-center rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[color:var(--accent-soft)]"
            >
              Mở cố vấn
            </Link>
          }
        >
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Tiến độ CTĐT</p>
              <p className="mt-3 text-2xl font-semibold">{String(data?.advisor_summary.completionPercent ?? 0)}%</p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[color:var(--text-soft)]">Degree audit</p>
            </div>
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Risk score</p>
              <p className="mt-3 text-2xl font-semibold">
                {String(data?.advisor_summary.riskLevel ?? "LOW")} • {String(data?.advisor_summary.riskScore ?? 0)}
              </p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[color:var(--text-soft)]">Rủi ro học tập</p>
            </div>
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Gợi ý kỳ tới</p>
              <p className="mt-3 text-2xl font-semibold">{String(data?.advisor_summary.nextSemesterCredits ?? 0)} TC</p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[color:var(--text-soft)]">
                {String(data?.advisor_summary.blockingCourses ?? 0)} môn đang chặn
              </p>
            </div>
          </div>
        </AppCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <AppCard title="Thông báo mới" subtitle="Ưu tiên bài mới từ UIT chính thức và các nhóm có ảnh hưởng trực tiếp đến sinh viên.">
          <div className="space-y-3">
            {data?.announcements.map((item) => (
              <a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium">{item.title}</p>
                    <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.group_name}</p>
                  </div>
                  <Badge tone="default">{item.group_name}</Badge>
                </div>
              </a>
            ))}
          </div>
        </AppCard>

        <AppCard title="Deadline gần tới" subtitle="Danh sách việc cần làm được kéo lên theo hạn chót gần nhất.">
          <div className="space-y-3">
            {data?.upcoming_tasks.map((task) => (
              <div key={task.id} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium">{task.title}</p>
                    <p className="mt-2 text-sm text-[color:var(--text-muted)]">{task.task_type}</p>
                  </div>
                  <Badge tone={task.due_at ? "accent" : "default"}>{formatDeadlineDistance(task.due_at)}</Badge>
                </div>
                <div className="mt-4 flex items-center gap-2 text-sm text-[color:var(--text-soft)]">
                  <Clock3 className="h-4 w-4" />
                  {formatDateTime(task.due_at)}
                </div>
              </div>
            ))}
          </div>
        </AppCard>
      </div>

      <AppCard title="Lịch hôm nay" subtitle="Hiển thị cả lịch học và lịch thi gần nhất để bạn không bị bỏ sót mốc quan trọng.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data?.today_schedule.map((item) => (
            <div key={`${item.title}-${item.starts_at}`} className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <Badge tone={item.item_type === "LỊCH THI" ? "warn" : "accent"}>{item.item_type}</Badge>
              <p className="mt-4 font-medium">{item.title}</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.location ?? "Chưa có phòng"}</p>
              <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(item.starts_at)}</p>
            </div>
          ))}
        </div>
      </AppCard>
    </AppShell>
  );
}
