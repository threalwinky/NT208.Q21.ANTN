"use client";

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import {
  completeTask,
  createTask,
  getClassSchedule,
  getExamSchedule,
  getTasks,
} from "@/lib/api";
import { formatDateTime, formatDeadlineDistance } from "@/lib/format";

type PlannerTask = {
  id: number;
  title: string;
  task_type: string;
  priority: string;
  due_at?: string | null;
  status: string;
};

function toDateTimeLocalValue(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function sortTasksByDueDate(items: PlannerTask[]) {
  return [...items].sort((left, right) => {
    const leftTime = left.due_at ? new Date(left.due_at).getTime() : Number.POSITIVE_INFINITY;
    const rightTime = right.due_at ? new Date(right.due_at).getTime() : Number.POSITIVE_INFINITY;
    return leftTime - rightTime;
  });
}

export default function PlannerPage() {
  const [classSchedule, setClassSchedule] = useState<Array<Record<string, unknown>>>([]);
  const [examSchedule, setExamSchedule] = useState<Array<Record<string, unknown>>>([]);
  const [tasks, setTasks] = useState<PlannerTask[]>([]);
  const [title, setTitle] = useState("Nhắc đăng ký học phần");
  const [taskType, setTaskType] = useState("Học vụ");
  const [dueAt, setDueAt] = useState(() => toDateTimeLocalValue(new Date(Date.now() + 3 * 86400000)));

  async function refresh() {
    const [classes, exams, tasksData] = await Promise.all([getClassSchedule(), getExamSchedule(), getTasks()]);
    setClassSchedule(classes);
    setExamSchedule(exams);
    setTasks(sortTasksByDueDate(tasksData as PlannerTask[]));
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      const [classes, exams, tasksData] = await Promise.all([getClassSchedule(), getExamSchedule(), getTasks()]);
      if (!mounted) {
        return;
      }
      setClassSchedule(classes);
      setExamSchedule(exams);
      setTasks(sortTasksByDueDate(tasksData as PlannerTask[]));
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell
      pageTitle="Lịch và nhắc việc"
      pageDescription="Quản lý lịch học, lịch thi, deadline đồ án và các việc học vụ theo một luồng nhìn dễ quét hơn."
    >
      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr] xl:gap-6">
        <AppCard title="Lịch học" subtitle="Bản xem nhanh theo từng môn để bạn kiểm tra block thời gian trong tuần.">
          <div className="space-y-3">
            {classSchedule.map((item) => (
              <div key={String(item.id)} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium">{String(item.course_name)}</p>
                    <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                      {String(item.course_code)} • {String(item.room_name ?? "Chưa có phòng")}
                    </p>
                  </div>
                  <Badge tone="accent">Thứ {String(item.weekday)}</Badge>
                </div>
                <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(String(item.starts_at ?? ""))}</p>
              </div>
            ))}
          </div>
        </AppCard>

        <AppCard title="Lịch thi" subtitle="Các mốc thi được tách riêng để bạn gắn nhắc việc và tránh trùng deadline.">
          <div className="space-y-3">
            {examSchedule.map((item) => (
              <div key={String(item.id)} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex items-center justify-between gap-4">
                  <p className="font-medium">{String(item.course_name)}</p>
                  <Badge tone="warn">{String(item.exam_type ?? "Lịch thi")}</Badge>
                </div>
                <p className="mt-2 text-sm text-[color:var(--text-muted)]">{String(item.room_name ?? "Chưa có phòng")}</p>
                <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(String(item.starts_at ?? ""))}</p>
              </div>
            ))}
          </div>
        </AppCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr] xl:gap-6">
        <AppCard title="Tạo việc mới" subtitle="Thêm nhanh một nhắc việc học vụ hoặc deadline cá nhân.">
          <div className="space-y-4">
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 outline-none"
              placeholder="Tên việc cần làm"
            />
            <select
              value={taskType}
              onChange={(event) => setTaskType(event.target.value)}
              className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 outline-none"
            >
              <option>Học vụ</option>
              <option>Deadline</option>
              <option>Đồ án</option>
              <option>Học phí</option>
            </select>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[color:var(--text-primary)]">Deadline</span>
              <input
                type="datetime-local"
                value={dueAt}
                onChange={(event) => setDueAt(event.target.value)}
                className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 outline-none"
              />
            </label>
            <button
              type="button"
              onClick={async () => {
                await createTask({
                  title,
                  task_type: taskType,
                  priority: "MEDIUM",
                  due_at: dueAt ? new Date(dueAt).toISOString() : null,
                });
                await refresh();
              }}
              className="btn-primary inline-flex h-11 items-center gap-2 rounded-2xl px-5 text-sm font-semibold transition"
            >
              <Plus className="h-4 w-4" />
              Thêm nhắc việc
            </button>
          </div>
        </AppCard>

        <AppCard title="Danh sách việc cần làm" subtitle="Xem theo list trước; có thể mở rộng sang calendar hoặc kanban ở bước tiếp theo.">
          <div className="space-y-3">
            {tasks.length === 0 ? (
              <div className="rounded-[22px] border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5 text-sm text-[color:var(--text-muted)]">
                Không còn việc nào đang mở.
              </div>
            ) : (
              tasks.map((item) => (
                <div key={item.id} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.title}</p>
                      <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.task_type}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={item.due_at ? "accent" : "default"}>{formatDeadlineDistance(item.due_at)}</Badge>
                      <button
                        type="button"
                        onClick={async () => {
                          await completeTask(item.id);
                          await refresh();
                        }}
                        className="btn-secondary inline-flex h-11 items-center rounded-2xl px-4 text-sm font-medium transition"
                      >
                        Đánh dấu xong
                      </button>
                    </div>
                  </div>
                  <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(item.due_at ?? "")}</p>
                </div>
              ))
            )}
          </div>
        </AppCard>
      </div>
    </AppShell>
  );
}
