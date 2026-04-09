"use client";

import { RefreshCcw, ScanSearch } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge, StatCard } from "@/components/ui";
import {
  getAdminOverview,
  getAdminSources,
  getConfigs,
  getCrawlerLogs,
  reindexAll,
  runKnowledgeRefresh,
  runCrawl,
  updateAdminSource,
  upsertConfig,
} from "@/lib/api";

export default function AdminPage() {
  const [overview, setOverview] = useState<Record<string, number>>({});
  const [sources, setSources] = useState<Array<Record<string, unknown>>>([]);
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [configs, setConfigs] = useState<Array<Record<string, unknown>>>([]);
  const [promptValue, setPromptValue] = useState(
    "Bạn là Studify, trợ lý đồng hành cho sinh viên UIT. Trả lời tiếng Việt, rõ, gọn, đúng nguồn và thân thiện."
  );

  async function refresh() {
    const [overviewData, sourcesData, logsData, configData] = await Promise.all([
      getAdminOverview(),
      getAdminSources(),
      getCrawlerLogs(),
      getConfigs(),
    ]);
    setOverview(overviewData);
    setSources(sourcesData);
    setLogs(logsData);
    setConfigs(configData);
    const promptConfig = configData.find((item) => String(item.key) === "chat_system_prompt");
    if (promptConfig && typeof promptConfig.value_json === "object" && promptConfig.value_json) {
      setPromptValue(String((promptConfig.value_json as { prompt?: string }).prompt ?? promptValue));
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      const [overviewData, sourcesData, logsData, configData] = await Promise.all([
        getAdminOverview(),
        getAdminSources(),
        getCrawlerLogs(),
        getConfigs(),
      ]);
      if (!mounted) {
        return;
      }
      setOverview(overviewData);
      setSources(sourcesData);
      setLogs(logsData);
      setConfigs(configData);
      const promptConfig = configData.find((item) => String(item.key) === "chat_system_prompt");
      if (promptConfig && typeof promptConfig.value_json === "object" && promptConfig.value_json) {
        setPromptValue(String((promptConfig.value_json as { prompt?: string }).prompt ?? ""));
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell
      pageTitle="Bảng quản trị dữ liệu"
      pageDescription="Theo dõi nguồn crawl, bật tắt nguồn, chạy lại indexing, điều chỉnh prompt và kiểm tra log để giữ knowledge base của Studify luôn gọn và đúng ngữ cảnh UIT."
    >
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Nguồn crawl" value={`${overview.totalSources ?? 0}`} hint="Đã đăng ký trong hệ thống" />
        <StatCard label="Tài liệu đã thu thập" value={`${overview.totalDocuments ?? 0}`} hint="HTML + PDF + nguồn tham khảo" />
        <StatCard label="FAQ quản trị" value={`${overview.totalFaqs ?? 0}`} hint="Cấu hình câu hỏi nhanh" />
        <StatCard label="Lần crawl gần đây" value={`${overview.recentCrawlerRuns ?? 0}`} hint="Tổng số bản ghi log" />
      </section>

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
          {logs.map((item) => (
            <div key={String(item.id)} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <ScanSearch className="h-4 w-4 text-[color:var(--accent)]" />
                  <p className="font-medium">Nguồn #{String(item.data_source_id)}</p>
                </div>
                <Badge tone={String(item.status).includes("FAILED") ? "warn" : "success"}>{String(item.status)}</Badge>
              </div>
              <p className="mt-3 text-sm text-[color:var(--text-muted)]">{String(item.message ?? "")}</p>
            </div>
          ))}
        </div>
      </AppCard>
    </AppShell>
  );
}
