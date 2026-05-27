"use client";

import { FileUp, RefreshCcw, ScanSearch } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge, StatCard } from "@/components/ui";
import {
  getAdminManualDocuments,
  getAdminOverview,
  getAdminRuntime,
  getAdminSources,
  getConfigs,
  getCrawlerLogs,
  reindexAll,
  runKnowledgeRefresh,
  runCrawl,
  uploadAdminDocument,
  updateAdminSource,
  upsertConfig,
  type AdminDocument,
  type AdminRuntime,
  type AdminUploadResult,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";

export default function AdminPage() {
  const [overview, setOverview] = useState<Record<string, number | string>>({});
  const [runtime, setRuntime] = useState<AdminRuntime | null>(null);
  const [sources, setSources] = useState<Array<Record<string, unknown>>>([]);
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [configs, setConfigs] = useState<Array<Record<string, unknown>>>([]);
  const [manualDocs, setManualDocs] = useState<AdminDocument[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<AdminUploadResult | null>(null);
  const [promptValue, setPromptValue] = useState(
    "Bạn là Studify, trợ lý đồng hành cho sinh viên UIT. Trả lời tiếng Việt, rõ, gọn, đúng nguồn và thân thiện."
  );
  const [uploadTitle, setUploadTitle] = useState("Thông báo mới từ quản trị");
  const [uploadCategory, setUploadCategory] = useState("ANNOUNCEMENT");
  const [uploadGroupName, setUploadGroupName] = useState("Thông báo quản trị");
  const [uploadTags, setUploadTags] = useState("uit, học vụ");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadOfficial, setUploadOfficial] = useState(true);
  const [uploadAnnouncement, setUploadAnnouncement] = useState(true);

  async function refresh() {
    setError("");
    const [overviewData, runtimeData, sourcesData, logsData, configData, manualDocsData] = await Promise.all([
      getAdminOverview(),
      getAdminRuntime(),
      getAdminSources(),
      getCrawlerLogs(),
      getConfigs(),
      getAdminManualDocuments(),
    ]);
    setOverview(overviewData);
    setRuntime(runtimeData);
    setSources(sourcesData);
    setLogs(logsData);
    setConfigs(configData);
    setManualDocs(manualDocsData);
    const promptConfig = configData.find((item) => String(item.key) === "chat_system_prompt");
    if (promptConfig && typeof promptConfig.value_json === "object" && promptConfig.value_json) {
      setPromptValue(String((promptConfig.value_json as { prompt?: string }).prompt ?? promptValue));
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [overviewData, runtimeData, sourcesData, logsData, configData, manualDocsData] = await Promise.all([
          getAdminOverview(),
          getAdminRuntime(),
          getAdminSources(),
          getCrawlerLogs(),
          getConfigs(),
          getAdminManualDocuments(),
        ]);
        if (!mounted) {
          return;
        }
        setOverview(overviewData);
        setRuntime(runtimeData);
        setSources(sourcesData);
        setLogs(logsData);
        setConfigs(configData);
        setManualDocs(manualDocsData);
        const promptConfig = configData.find((item) => String(item.key) === "chat_system_prompt");
        if (promptConfig && typeof promptConfig.value_json === "object" && promptConfig.value_json) {
          setPromptValue(String((promptConfig.value_json as { prompt?: string }).prompt ?? ""));
        }
      } catch (caughtError) {
        if (mounted) {
          setError(caughtError instanceof Error ? caughtError.message : "Không tải được dữ liệu quản trị.");
        }
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  const runtimeStatus = String(runtime?.refresh_runtime?.status ?? overview.refreshStatus ?? "IDLE");
  const latestSampleError = logs.find((item) => {
    const detail = item.detail_json;
    return Boolean(detail && typeof detail === "object" && Array.isArray((detail as { sample_errors?: unknown[] }).sample_errors));
  });

  return (
    <AppShell
      pageTitle="Bảng quản trị dữ liệu"
      pageDescription="Theo dõi nguồn crawl, bật tắt nguồn, chạy lại indexing, điều chỉnh prompt và kiểm tra log để giữ knowledge base của Studify luôn gọn và đúng ngữ cảnh UIT."
    >
      {error ? (
        <div className="rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Nguồn crawl" value={`${overview.totalSources ?? 0}`} hint="Đã đăng ký trong hệ thống" />
        <StatCard label="Tài liệu đã thu thập" value={`${overview.totalDocuments ?? 0}`} hint="HTML + PDF + nguồn tham khảo" />
        <StatCard label="FAQ quản trị" value={`${overview.totalFaqs ?? 0}`} hint="Cấu hình câu hỏi nhanh" />
        <StatCard label="Hàng đợi nền" value={`${runtime?.queue_size ?? overview.queueSize ?? 0}`} hint={`Refresh: ${runtimeStatus}`} />
      </section>

      <div className="grid gap-4 xl:grid-cols-[0.98fr_1.02fr]">
        <AppCard
          title="Nạp tài liệu vào RAG"
          subtitle="Upload PDF, ảnh, CSV hoặc XLSX để đưa thẳng vào vector search. Hợp cho kế hoạch năm, học bổng, công văn mới."
          action={<Badge tone="accent">{manualDocs.length} tài liệu thủ công</Badge>}
        >
          <div className="space-y-4">
            <input
              value={uploadTitle}
              onChange={(event) => setUploadTitle(event.target.value)}
              className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              placeholder="Tiêu đề tài liệu"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                value={uploadCategory}
                onChange={(event) => setUploadCategory(event.target.value)}
                className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              >
                <option value="ANNOUNCEMENT">Thông báo</option>
                <option value="ACADEMIC">Học vụ</option>
                <option value="SCHOLARSHIP">Học bổng</option>
                <option value="TUITION">Học phí</option>
                <option value="PROCEDURE">Thủ tục</option>
                <option value="SKILL">Kỹ năng</option>
              </select>
              <input
                value={uploadGroupName}
                onChange={(event) => setUploadGroupName(event.target.value)}
                className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
                placeholder="Nhóm hiển thị"
              />
            </div>
            <input
              value={uploadTags}
              onChange={(event) => setUploadTags(event.target.value)}
              className="w-full rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              placeholder="Tag, cách nhau bởi dấu phẩy"
            />
            <label className="block rounded-[22px] border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-5 text-sm text-[color:var(--text-muted)]">
              <span className="mb-2 block font-medium text-[color:var(--text-primary)]">Tệp tài liệu</span>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.csv,.xlsx,.txt,.md"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                className="block w-full text-sm"
              />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex items-center gap-3 rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm">
                <input type="checkbox" checked={uploadOfficial} onChange={(event) => setUploadOfficial(event.target.checked)} />
                Đánh dấu là nguồn UIT chính thức
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm">
                <input type="checkbox" checked={uploadAnnouncement} onChange={(event) => setUploadAnnouncement(event.target.checked)} />
                Đồng thời tạo announcement
              </label>
            </div>
            <button
              type="button"
              disabled={!uploadFile || uploading}
              onClick={async () => {
                if (!uploadFile) {
                  return;
                }
                try {
                  setUploading(true);
                  setError("");
                  const formData = new FormData();
                  formData.set("file", uploadFile);
                  formData.set("title", uploadTitle);
                  formData.set("category_code", uploadCategory);
                  formData.set("group_name", uploadGroupName);
                  formData.set("tags", uploadTags);
                  formData.set("is_official_uit", String(uploadOfficial));
                  formData.set("create_announcement", String(uploadAnnouncement));
                  const result = await uploadAdminDocument(formData);
                  setUploadResult(result);
                  await refresh();
                } catch (caughtError) {
                  setError(caughtError instanceof Error ? caughtError.message : "Không upload được tài liệu.");
                } finally {
                  setUploading(false);
                }
              }}
              className="btn-primary inline-flex h-12 items-center gap-2 rounded-2xl px-5 text-sm font-semibold transition disabled:opacity-60"
            >
              <FileUp className="h-4 w-4" />
              {uploading ? "Đang nạp vào RAG..." : "Upload và index"}
            </button>

            {uploadResult ? (
              <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-sm">
                <p className="font-medium">{uploadResult.title}</p>
                <p className="mt-2 text-[color:var(--text-muted)]">
                  {uploadResult.status} • {uploadResult.chunk_count} chunk • {uploadResult.file_type}
                  {uploadResult.used_ocr ? " • có OCR" : ""}
                </p>
              </div>
            ) : null}
          </div>
        </AppCard>

        <AppCard title="Tài liệu thủ công gần đây" subtitle="Kiểm tra nhanh tài liệu admin đã nạp vào knowledge base và vector search.">
          <div className="space-y-3">
            {manualDocs.map((item) => (
              <div key={item.id} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{item.title}</p>
                    <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                      {item.group_name ?? "Tài liệu thủ công"} • {item.file_type ?? "text"}
                    </p>
                  </div>
                  <Badge tone={item.is_official_uit ? "success" : "warn"}>{item.is_official_uit ? "Nguồn UIT" : "Tham khảo"}</Badge>
                </div>
                <p className="mt-3 text-xs uppercase tracking-[0.14em] text-[color:var(--text-soft)]">
                  {item.updated_source_at ? formatDateTime(item.updated_source_at) : "Chưa rõ thời gian"}
                </p>
                {item.vector_metadata?.storage_path ? (
                  <p className="mt-2 break-all text-xs text-[color:var(--text-muted)]">{String(item.vector_metadata.storage_path)}</p>
                ) : null}
              </div>
            ))}
            {!manualDocs.length ? (
              <div className="rounded-[22px] border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-sm text-[color:var(--text-muted)]">
                Chưa có tài liệu thủ công nào.
              </div>
            ) : null}
          </div>
        </AppCard>
      </div>

      <AppCard title="Trạng thái làm mới corpus" subtitle="Theo dõi job nền để biết lúc nào crawler, import và re-index đang chạy hoặc thất bại.">
        <div className="grid gap-4 xl:grid-cols-[0.86fr_1.14fr]">
          <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={runtimeStatus.includes("FAILED") ? "warn" : "accent"}>{runtimeStatus}</Badge>
              <Badge tone="default">Queue {runtime?.queue_size ?? 0}</Badge>
            </div>
            <p className="mt-4 text-sm leading-6 text-[color:var(--text-primary)]">
              {String(runtime?.refresh_runtime?.last_message ?? "Chưa có lượt làm mới corpus nào.")}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Lần thành công gần nhất</p>
              <p className="mt-3 text-sm font-medium text-[color:var(--text-primary)]">
                {runtime?.refresh_runtime?.last_success_at ? formatDateTime(String(runtime.refresh_runtime.last_success_at)) : "Chưa có"}
              </p>
            </div>
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <p className="text-sm text-[color:var(--text-muted)]">Lần kế tiếp</p>
              <p className="mt-3 text-sm font-medium text-[color:var(--text-primary)]">
                {runtime?.refresh_runtime?.next_run_at ? formatDateTime(String(runtime.refresh_runtime.next_run_at)) : "Chưa lên lịch"}
              </p>
            </div>
          </div>
        </div>
      </AppCard>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <AppCard
          title="Nguồn dữ liệu"
          subtitle="Bật hoặc tắt từng nguồn theo tình trạng dữ liệu và độ ổn định của crawler."
          action={
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={async () => {
                  await runKnowledgeRefresh();
                  await refresh();
                }}
                className="inline-flex items-center gap-2 rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[color:var(--surface-soft)]"
              >
                <RefreshCcw className="h-4 w-4" />
                Làm mới corpus
              </button>
              <button
                type="button"
                onClick={async () => {
                  await reindexAll();
                  await refresh();
                }}
                className="inline-flex items-center gap-2 rounded-2xl bg-[color:var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[color:var(--accent-strong)]"
              >
                <RefreshCcw className="h-4 w-4" />
                Reindex
              </button>
            </div>
          }
        >
          <div className="space-y-3">
            {sources.map((item) => (
              <div key={String(item.id)} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{String(item.name)}</p>
                    <p className="mt-2 text-sm text-[color:var(--text-muted)]">{String(item.base_url)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={Boolean(item.is_enabled) ? "success" : "warn"}>
                      {Boolean(item.is_enabled) ? "Đang bật" : "Đang tắt"}
                    </Badge>
                    <button
                      type="button"
                      onClick={async () => {
                        await updateAdminSource(Number(item.id), !Boolean(item.is_enabled));
                        await refresh();
                      }}
                      className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-xs text-[color:var(--text-primary)] transition hover:bg-[color:var(--accent-soft)]"
                    >
                      Bật/Tắt
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        await runCrawl(Number(item.id));
                        await refresh();
                      }}
                      className="rounded-xl bg-[color:var(--accent)] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[color:var(--accent-strong)]"
                    >
                      Crawl lại
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </AppCard>

        <AppCard title="Prompt hệ thống" subtitle="Điều chỉnh giọng điệu trả lời để bám ngữ cảnh sinh viên UIT và phân biệt rõ nguồn chính thức.">
          <textarea
            value={promptValue}
            onChange={(event) => setPromptValue(event.target.value)}
            className="min-h-[220px] w-full rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm leading-6 outline-none"
          />
          <button
            type="button"
            onClick={async () => {
              await upsertConfig({
                key: "chat_system_prompt",
                value_json: { prompt: promptValue },
                description: "Prompt hệ thống cho chatbot chung.",
              });
              await refresh();
            }}
            className="mt-4 rounded-2xl bg-[color:var(--accent)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[color:var(--accent-strong)]"
          >
            Lưu prompt
          </button>

          <div className="mt-4 rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
            <p className="text-sm font-medium">Cấu hình hiện có</p>
            <div className="mt-3 space-y-2">
              {configs.map((item) => (
                <div key={String(item.id)} className="rounded-2xl bg-[color:var(--surface)] px-3 py-2 text-sm text-[color:var(--text-muted)]">
                  {String(item.key)}
                </div>
              ))}
            </div>
          </div>
        </AppCard>
      </div>

      <AppCard title="Log crawler" subtitle="Theo dõi lượt crawl gần nhất để nhìn nhanh nguồn nào đang ổn, nguồn nào cần kiểm tra lại selector hoặc timeout.">
        <div className="space-y-3">
          {logs.map((item) => {
            const detail = item.detail_json as
              | {
                  processed_urls?: number;
                  skipped_urls?: number;
                  sample_errors?: Array<{ url?: string; error?: string }>;
                }
              | undefined;

            return (
              <div key={String(item.id)} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ScanSearch className="h-4 w-4 text-[color:var(--accent)]" />
                    <p className="font-medium">Nguồn #{String(item.data_source_id)}</p>
                  </div>
                  <Badge tone={String(item.status).includes("FAILED") ? "warn" : "success"}>{String(item.status)}</Badge>
                </div>
                <p className="mt-3 text-sm text-[color:var(--text-muted)]">{String(item.message ?? "")}</p>
                {detail ? (
                  <div className="mt-3 rounded-[18px] bg-[color:var(--surface)] p-3 text-xs text-[color:var(--text-muted)]">
                    <p>Đã xử lý: {detail.processed_urls ?? 0} URL</p>
                    <p>Bỏ qua: {detail.skipped_urls ?? 0} URL</p>
                    {detail.sample_errors && detail.sample_errors.length > 0 ? (
                      <p className="mt-2 line-clamp-3">
                        Lỗi mẫu: {detail.sample_errors[0]?.url ?? ""} · {detail.sample_errors[0]?.error ?? ""}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
          {!logs.length && latestSampleError === undefined ? (
            <div className="rounded-[22px] border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 text-sm text-[color:var(--text-muted)]">
              Chưa có log crawler nào trong phiên bản này.
            </div>
          ) : null}
        </div>
      </AppCard>
    </AppShell>
  );
}
