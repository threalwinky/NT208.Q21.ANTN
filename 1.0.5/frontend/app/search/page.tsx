"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import {
  searchStudify,
  getStudyDocuments,
  getAcademicEvents,
  getCourses,
  getDocuments,
  type Course,
} from "@/lib/api";
import { formatDate } from "@/lib/format";

// ─── Kiểu tab ────────────────────────────────────────────────────────────────

type TabId = "tim-nhanh" | "hoc-vu" | "mon-hoc" | "tai-lieu";

const TABS: { id: TabId; label: string }[] = [
  { id: "tim-nhanh", label: "Tìm nhanh" },
  { id: "hoc-vu", label: "Học vụ" },
  { id: "mon-hoc", label: "Môn học" },
  { id: "tai-lieu", label: "Tài liệu" },
];

// ─── Component chính ─────────────────────────────────────────────────────────

export default function SearchPage() {
  const [activeTab, setActiveTab] = useState<TabId>("tim-nhanh");

  // Trạng thái tab "Tìm nhanh"
  const [timNhanhQuery, setTimNhanhQuery] = useState("đăng ký học phần");
  const [timNhanhResult, setTimNhanhResult] = useState<Record<string, Array<Record<string, unknown>> | string> | null>(null);
  const [timNhanhLoading, setTimNhanhLoading] = useState(false);

  // Trạng thái tab "Học vụ"
  const [hocVuDocuments, setHocVuDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [hocVuEvents, setHocVuEvents] = useState<Array<Record<string, unknown>>>([]);
  const [hocVuLoaded, setHocVuLoaded] = useState(false);
  const [hocVuLoading, setHocVuLoading] = useState(false);

  // Trạng thái tab "Môn học"
  const [monHocQuery, setMonHocQuery] = useState("");
  const [monHocCourses, setMonHocCourses] = useState<Course[]>([]);
  const [monHocLoaded, setMonHocLoaded] = useState(false);
  const [monHocLoading, setMonHocLoading] = useState(false);

  // Trạng thái tab "Tài liệu"
  const [taiLieuQuery, setTaiLieuQuery] = useState("");
  const [taiLieuDocs, setTaiLieuDocs] = useState<Array<Record<string, unknown>>>([]);
  const [taiLieuLoaded, setTaiLieuLoaded] = useState(false);
  const [taiLieuLoading, setTaiLieuLoading] = useState(false);

  // Tải dữ liệu khi chuyển tab (chỉ lần đầu)
  useEffect(() => {
    if (activeTab === "hoc-vu" && !hocVuLoaded) {
      setHocVuLoading(true);
      Promise.all([getStudyDocuments(), getAcademicEvents()])
        .then(([docs, events]) => {
          setHocVuDocuments(docs);
          setHocVuEvents(events);
          setHocVuLoaded(true);
        })
        .finally(() => setHocVuLoading(false));
    }

    if (activeTab === "mon-hoc" && !monHocLoaded) {
      setMonHocLoading(true);
      getCourses("")
        .then((data) => {
          setMonHocCourses(data);
          setMonHocLoaded(true);
        })
        .finally(() => setMonHocLoading(false));
    }

    if (activeTab === "tai-lieu" && !taiLieuLoaded) {
      setTaiLieuLoading(true);
      getDocuments("")
        .then((data) => {
          setTaiLieuDocs(data);
          setTaiLieuLoaded(true);
        })
        .finally(() => setTaiLieuLoading(false));
    }
  }, [activeTab, hocVuLoaded, monHocLoaded, taiLieuLoaded]);

  // ── Hàm tìm kiếm ────────────────────────────────────────────────────────────

  async function runTimNhanh() {
    setTimNhanhLoading(true);
    try {
      setTimNhanhResult(await searchStudify(timNhanhQuery));
    } finally {
      setTimNhanhLoading(false);
    }
  }

  async function runMonHoc() {
    setMonHocLoading(true);
    try {
      setMonHocCourses(await getCourses(monHocQuery));
    } finally {
      setMonHocLoading(false);
    }
  }

  async function runTaiLieu() {
    setTaiLieuLoading(true);
    try {
      setTaiLieuDocs(await getDocuments(taiLieuQuery));
    } finally {
      setTaiLieuLoading(false);
    }
  }

  // ── Dữ liệu kết quả "Tìm nhanh" ─────────────────────────────────────────────

  const timNhanhDocuments =
    (timNhanhResult?.documents as Array<Record<string, unknown>> | undefined) ?? [];
  const timNhanhAnnouncements =
    (timNhanhResult?.announcements as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <AppShell
      pageTitle="Tìm kiếm"
      pageDescription="Tra cứu tài liệu, học vụ, môn học và thông báo UIT."
    >
      {/* Thanh tab pill */}
      <div className="flex flex-wrap gap-2 rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={[
              "rounded-full px-5 py-2 text-sm font-semibold transition",
              activeTab === tab.id
                ? "bg-[color:var(--accent)] text-white shadow-sm"
                : "text-[color:var(--text-muted)] hover:text-[color:var(--text)]",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Tìm nhanh ───────────────────────────────────────────────────── */}
      {activeTab === "tim-nhanh" && (
        <>
          <AppCard
            title="Tìm nhanh"
            subtitle="Phù hợp khi cần kiểm nguồn trước khi hỏi chatbot."
          >
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                value={timNhanhQuery}
                onChange={(e) => setTimNhanhQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void runTimNhanh()}
                placeholder="Nhập từ khóa cần tìm..."
                className="min-h-12 flex-1 rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm outline-none"
              />
              <button
                type="button"
                onClick={() => void runTimNhanh()}
                disabled={timNhanhLoading}
                className="btn-primary rounded-2xl px-5 py-3 text-sm font-semibold transition disabled:opacity-60"
              >
                {timNhanhLoading ? "Đang tìm..." : "Tìm"}
              </button>
            </div>
          </AppCard>

          {timNhanhResult && (
            <div className="grid gap-4 xl:grid-cols-2">
              <AppCard
                title="Tài liệu"
                subtitle={`${timNhanhDocuments.length} kết quả`}
              >
                <div className="space-y-3">
                  {timNhanhDocuments.length === 0 && (
                    <p className="text-sm text-[color:var(--text-muted)]">Không có kết quả.</p>
                  )}
                  {timNhanhDocuments.map((item) => (
                    <a
                      key={`doc-${String(item.id)}`}
                      href={String(item.url)}
                      target="_blank"
                      rel="noreferrer"
                      className="block rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                    >
                      <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>
                        {Boolean(item.is_official_uit) ? "UIT" : "Tham khảo"}
                      </Badge>
                      <p className="mt-3 font-medium">{String(item.title)}</p>
                      <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">
                        {String(item.summary ?? "")}
                      </p>
                    </a>
                  ))}
                </div>
              </AppCard>

              <AppCard
                title="Thông báo"
                subtitle={`${timNhanhAnnouncements.length} kết quả`}
              >
                <div className="space-y-3">
                  {timNhanhAnnouncements.length === 0 && (
                    <p className="text-sm text-[color:var(--text-muted)]">Không có kết quả.</p>
                  )}
                  {timNhanhAnnouncements.map((item) => (
                    <a
                      key={`ann-${String(item.id)}`}
                      href={String(item.url)}
                      target="_blank"
                      rel="noreferrer"
                      className="block rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                    >
                      <Badge tone="accent">{String(item.group_name ?? "Thông báo")}</Badge>
                      <p className="mt-3 font-medium">{String(item.title)}</p>
                      <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">
                        {String(item.summary ?? "")}
                      </p>
                    </a>
                  ))}
                </div>
              </AppCard>
            </div>
          )}
        </>
      )}

      {/* ── Tab: Học vụ ──────────────────────────────────────────────────────── */}
      {activeTab === "hoc-vu" && (
        <>
          {hocVuLoading && (
            <p className="text-sm text-[color:var(--text-muted)]">Đang tải dữ liệu học vụ...</p>
          )}
          {!hocVuLoading && (
            <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
              <AppCard
                title="Kho tài liệu học vụ"
                subtitle="Tài liệu được lọc theo nội dung học vụ, thủ tục, xét tốt nghiệp và học phí."
              >
                <div className="space-y-3">
                  {hocVuDocuments.length === 0 && (
                    <p className="text-sm text-[color:var(--text-muted)]">Chưa có tài liệu nào.</p>
                  )}
                  {hocVuDocuments.map((item) => (
                    <a
                      key={String(item.id)}
                      href={String(item.url)}
                      target="_blank"
                      rel="noreferrer"
                      className="block rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="font-medium">{String(item.title)}</p>
                        <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>
                          {Boolean(item.is_official_uit) ? "Nguồn UIT" : "Tham khảo"}
                        </Badge>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                        {String(item.summary ?? "")}
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2 text-xs text-[color:var(--text-soft)]">
                        <span>{String(item.group_name ?? "Tài liệu")}</span>
                        <span>•</span>
                        <span>{formatDate(String(item.updated_source_at ?? ""))}</span>
                      </div>
                    </a>
                  ))}
                </div>
              </AppCard>

              <AppCard
                title="Mốc học vụ sắp tới"
                subtitle="Những cột mốc nên chốt sớm để không bị dồn việc vào phút cuối."
              >
                <div className="space-y-3">
                  {hocVuEvents.length === 0 && (
                    <p className="text-sm text-[color:var(--text-muted)]">Chưa có sự kiện nào.</p>
                  )}
                  {hocVuEvents.map((item) => (
                    <div
                      key={String(item.id)}
                      className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-medium">{String(item.title)}</p>
                        <Badge tone="accent">{String(item.group_name)}</Badge>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                        {String(item.description ?? "")}
                      </p>
                      <p className="mt-4 text-sm text-[color:var(--text-soft)]">
                        {formatDate(String(item.starts_at ?? ""))}
                        {item.ends_at ? ` - ${formatDate(String(item.ends_at))}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </AppCard>
            </div>
          )}
        </>
      )}

      {/* ── Tab: Môn học ─────────────────────────────────────────────────────── */}
      {activeTab === "mon-hoc" && (
        <>
          <AppCard
            title="Tìm môn học"
            subtitle="Có thể tìm bằng mã môn hoặc tên môn."
          >
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                value={monHocQuery}
                onChange={(e) => setMonHocQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void runMonHoc()}
                placeholder="Ví dụ: NT208, cơ sở dữ liệu, an toàn mạng..."
                className="min-h-12 flex-1 rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm outline-none"
              />
              <button
                type="button"
                onClick={() => void runMonHoc()}
                disabled={monHocLoading}
                className="btn-primary rounded-2xl px-5 py-3 text-sm font-semibold transition disabled:opacity-60"
              >
                {monHocLoading ? "Đang tìm..." : "Tìm kiếm"}
              </button>
            </div>
          </AppCard>

          {monHocLoading && (
            <p className="text-sm text-[color:var(--text-muted)]">Đang tải danh sách môn học...</p>
          )}
          {!monHocLoading && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {monHocCourses.length === 0 && (
                <p className="col-span-full text-sm text-[color:var(--text-muted)]">
                  Không tìm thấy môn học phù hợp.
                </p>
              )}
              {monHocCourses.map((course) => (
                <div
                  key={course.id}
                  className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <Badge tone="accent">{course.code}</Badge>
                    <Badge tone="default">{course.credits} tín chỉ</Badge>
                  </div>
                  <h2 className="mt-4 text-lg font-semibold">{course.name}</h2>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">
                    {course.description ?? "Chưa có mô tả chi tiết."}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge tone="success">{course.category}</Badge>
                    {course.requirement_groups.map((group) => (
                      <Badge key={group} tone="default">{group}</Badge>
                    ))}
                  </div>
                  {course.prerequisite_codes.length > 0 && (
                    <p className="mt-4 text-sm text-[color:var(--text-soft)]">
                      Tiên quyết: {course.prerequisite_codes.join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Tab: Tài liệu ────────────────────────────────────────────────────── */}
      {activeTab === "tai-lieu" && (
        <>
          <AppCard
            title="Lọc tài liệu"
            subtitle="Tìm trong title, summary và nội dung đã làm sạch."
          >
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                value={taiLieuQuery}
                onChange={(e) => setTaiLieuQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void runTaiLieu()}
                placeholder="Tìm học phí, tốt nghiệp, học bổng..."
                className="min-h-12 flex-1 rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 text-sm outline-none"
              />
              <button
                type="button"
                onClick={() => void runTaiLieu()}
                disabled={taiLieuLoading}
                className="btn-primary rounded-2xl px-5 py-3 text-sm font-semibold transition disabled:opacity-60"
              >
                {taiLieuLoading ? "Đang tìm..." : "Tìm tài liệu"}
              </button>
            </div>
          </AppCard>

          {taiLieuLoading && (
            <p className="text-sm text-[color:var(--text-muted)]">Đang tải tài liệu...</p>
          )}
          {!taiLieuLoading && (
            <div className="grid gap-4 xl:grid-cols-2">
              {taiLieuDocs.length === 0 && (
                <p className="col-span-full text-sm text-[color:var(--text-muted)]">
                  Không tìm thấy tài liệu phù hợp.
                </p>
              )}
              {taiLieuDocs.map((item) => (
                <a
                  key={String(item.id)}
                  href={String(item.url)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition hover:border-[color:var(--accent)]/30"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>
                      {Boolean(item.is_official_uit) ? "Nguồn UIT" : "Tham khảo"}
                    </Badge>
                    <Badge tone="default">{String(item.group_name ?? "Tài liệu")}</Badge>
                  </div>
                  <h2 className="mt-4 text-lg font-semibold">{String(item.title)}</h2>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                    {String(item.summary ?? "Chưa có tóm tắt.")}
                  </p>
                  <p className="mt-4 text-sm text-[color:var(--text-soft)]">
                    Cập nhật: {formatDate(String(item.updated_source_at ?? ""))}
                  </p>
                </a>
              ))}
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
