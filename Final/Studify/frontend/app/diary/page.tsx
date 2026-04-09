"use client";

import { BarChart3, ChevronDown, ChevronUp, Music4, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import { createMoodCheckin, getEnergyInsight, getMoodJournals, getMoods, getSupportResources, previewEnergyInsight, type EnergyInsight, type MoodJournal } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const JOURNAL_PREVIEW_COUNT = 4;

export default function DiaryPage() {
  const [moods, setMoods] = useState<Array<Record<string, unknown>>>([]);
  const [journals, setJournals] = useState<MoodJournal[]>([]);
  const [resources, setResources] = useState<Array<Record<string, unknown>>>([]);
  const [insight, setInsight] = useState<EnergyInsight | null>(null);
  const [selectedMood, setSelectedMood] = useState<number | null>(null);
  const [note, setNote] = useState("Hơi mệt vì deadline dồn nhưng vẫn muốn sắp xếp lại.");
  const [showAllJournals, setShowAllJournals] = useState(false);
  const [isInsightRefreshing, setIsInsightRefreshing] = useState(false);

  async function refresh() {
    const [moodData, journalData, resourceData, insightData] = await Promise.all([
      getMoods(),
      getMoodJournals(),
      getSupportResources(),
      getEnergyInsight(),
    ]);
    setMoods(moodData);
    setJournals(journalData);
    setResources(resourceData);
    setInsight(insightData);
    if (!selectedMood && moodData[0]?.id) {
      const preferredMood = moodData.find((item) => String(item.display_name) === String(insightData.latest_mood_label ?? ""));
      setSelectedMood(Number(preferredMood?.id ?? moodData[0].id));
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      const [moodData, journalData, resourceData, insightData] = await Promise.all([
        getMoods(),
        getMoodJournals(),
        getSupportResources(),
        getEnergyInsight(),
      ]);
      if (!mounted) {
        return;
      }
      setMoods(moodData);
      setJournals(journalData);
      setResources(resourceData);
      setInsight(insightData);
      if (moodData[0]?.id) {
        const preferredMood = moodData.find((item) => String(item.display_name) === String(insightData.latest_mood_label ?? ""));
        setSelectedMood((current) => current ?? Number(preferredMood?.id ?? moodData[0].id));
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedMood) {
      return;
    }

    let active = true;
    const timer = window.setTimeout(async () => {
      setIsInsightRefreshing(true);
      try {
        const preview = await previewEnergyInsight({
          mood_state_id: selectedMood,
          short_note: note,
        });
        if (active) {
          setInsight(preview);
        }
      } finally {
        if (active) {
          setIsInsightRefreshing(false);
        }
      }
    }, 320);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [selectedMood, note]);

  const visibleJournals = showAllJournals ? journals : journals.slice(0, JOURNAL_PREVIEW_COUNT);
  const hasHiddenJournals = journals.length > JOURNAL_PREVIEW_COUNT;

  return (
    <AppShell
      pageTitle="Nhật ký"
      pageDescription="Ghi một dòng ngắn để Studify đọc nhịp năng lượng hiện tại của bạn và gợi ý một bước tiếp theo vừa sức."
    >
      <div className="grid gap-4 xl:grid-cols-[0.82fr_1.18fr]">
        <AppCard title="Hôm nay bạn thế nào?" subtitle="Chọn tâm trạng gần nhất rồi viết vài dòng ngắn. Năng lượng sẽ được phân tích tự động.">
          <div className="grid gap-3 sm:grid-cols-2">
            {moods.map((item) => (
              <button
                key={String(item.id)}
                type="button"
                onClick={() => setSelectedMood(Number(item.id))}
                className={`rounded-[22px] border p-4 text-left transition ${
                  selectedMood === Number(item.id)
                    ? "border-transparent bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                    : "border-[color:var(--line)] bg-[color:var(--surface-soft)] hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                }`}
              >
                <p className="font-medium">{String(item.display_name)}</p>
                <p className="mt-2 text-sm text-[color:var(--text-muted)]">{String(item.description ?? "Một nhịp cảm xúc trong ngày.")}</p>
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="mt-4 min-h-[120px] w-full rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm leading-6 outline-none"
            placeholder="Viết ngắn vài dòng nếu bạn muốn..."
          />
          <button
            type="button"
            onClick={async () => {
              await createMoodCheckin({
                mood_state_id: selectedMood,
                short_note: note,
                needs_human_support: false,
              });
              await refresh();
            }}
            className="btn-primary mt-4 rounded-2xl px-5 py-3 text-sm font-semibold transition"
          >
            Lưu nhật ký hôm nay
          </button>
        </AppCard>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                <BarChart3 className="h-4 w-4 text-[color:var(--accent)]" />
                Năng lượng
              </div>
              <p className="mt-3 text-3xl font-semibold tracking-tight">{insight?.latest_energy_level ?? 3}/5</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">{insight?.latest_energy_label ?? "Trung bình"}</p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                {insight?.trend === "DOWN" ? (
                  <TrendingDown className="h-4 w-4 text-amber-500" />
                ) : insight?.trend === "UP" ? (
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Sparkles className="h-4 w-4 text-[color:var(--accent)]" />
                )}
                Xu hướng
              </div>
              <p className="mt-3 text-3xl font-semibold tracking-tight">{insight?.average_energy_level ?? 3}</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                {insight?.trend === "DOWN" ? "Đang chùng xuống" : insight?.trend === "UP" ? "Đang lên" : "Ổn định"}
              </p>
            </div>
            <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
              <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                <Music4 className="h-4 w-4 text-[color:var(--accent)]" />
                Gợi ý
              </div>
              <p className="mt-3 text-lg font-semibold">{insight?.music_theme_label ?? "Nhạc gợi ý"}</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">{insight?.summary}</p>
            </div>
          </div>

          <AppCard title="Phân tích nhịp gần nhất" subtitle="Studify đọc từ tâm trạng và vài cụm trong nhật ký để ước lượng mức năng lượng hiện tại.">
            <div className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="accent">{insight?.latest_mood_label ?? "Chưa có tâm trạng"}</Badge>
                <Badge tone="default">{insight?.latest_energy_label ?? "Trung bình"}</Badge>
                {(insight?.signals ?? []).map((signal) => (
                  <Badge key={signal} tone="default">
                    {signal}
                  </Badge>
                ))}
              </div>
              <p className="mt-4 text-sm leading-6 text-[color:var(--text-primary)]">{insight?.summary}</p>
              <div className="mt-4 flex gap-2">
                {(insight?.energy_series ?? []).map((value, index) => (
                  <div key={`${value}-${index}`} className="flex-1 rounded-full bg-[color:var(--surface)] p-1">
                    <div className="rounded-full bg-[color:var(--accent)] text-center text-xs font-medium text-white" style={{ width: `${(value / 5) * 100}%` }}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </AppCard>

          <AppCard
            title="Bài hát gợi ý"
            subtitle={isInsightRefreshing ? "Studify đang đổi vibe theo mood và dòng nhật ký hiện tại..." : "Studify chọn ngẫu nhiên theo mood hiện tại của bạn và hiển thị trực tiếp bằng Spotify embed."}
          >
            {(insight?.music_tracks ?? []).length > 0 ? (
              <div className="grid items-start gap-4 xl:grid-cols-2">
                {insight?.music_tracks.map((track) => (
                  <iframe
                    key={`${track.embed_url}-${track.title}`}
                    title={`${track.title} - ${track.artist}`}
                    src={track.embed_url}
                    loading="lazy"
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    className="block h-[152px] w-full overflow-hidden rounded-[18px]"
                    style={{ border: 0 }}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-[22px] border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5 text-sm text-[color:var(--text-muted)]">
                Chưa lấy được danh sách bài hát ở lần này. Bạn lưu lại một dòng ngắn rồi thử tải lại để Studify chọn lại vibe phù hợp hơn.
              </div>
            )}
          </AppCard>

          <AppCard title="Nhật ký gần đây" subtitle="Nhìn lại vài dòng gần nhất để xem tuần này bạn đang dồn vào đâu.">
            <div className="space-y-3">
              {visibleJournals.map((item) => (
                <div key={item.id} className="rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-medium">{item.mood_label ?? "Nhật ký"}</p>
                    <Badge tone="accent">
                      {item.energy_label} • {item.energy_level}/5
                    </Badge>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">{item.short_note ?? ""}</p>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.energy_summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {item.signals.map((signal) => (
                      <Badge key={signal} tone="default">
                        {signal}
                      </Badge>
                    ))}
                  </div>
                  <p className="mt-4 text-sm text-[color:var(--text-soft)]">{formatDateTime(item.created_at)}</p>
                </div>
              ))}
              {hasHiddenJournals ? (
                <button
                  type="button"
                  onClick={() => setShowAllJournals((current) => !current)}
                  className="btn-secondary inline-flex items-center gap-2 rounded-[18px] px-4 py-2.5 text-sm font-medium transition"
                >
                  {showAllJournals ? (
                    <>
                      Thu gọn
                      <ChevronUp className="h-4 w-4" />
                    </>
                  ) : (
                    <>
                      Xem thêm
                      <ChevronDown className="h-4 w-4" />
                    </>
                  )}
                </button>
              ) : null}
            </div>
          </AppCard>

          <AppCard title="Nguồn hỗ trợ trong trường" subtitle="Các kênh để bạn tìm thêm một điểm chạm nhẹ khi đang cần sắp xếp lại.">
            <div className="space-y-3">
              {resources.map((item) => (
                <a
                  key={String(item.id)}
                  href={String(item.link_url ?? "#")}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-[22px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium">{String(item.title)}</p>
                      <p className="mt-2 text-sm text-[color:var(--text-muted)]">{String(item.description ?? "")}</p>
                    </div>
                    <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>{String(item.resource_type)}</Badge>
                  </div>
                  <p className="mt-4 text-sm text-[color:var(--text-soft)]">{String(item.owner_unit ?? "")}</p>
                </a>
              ))}
            </div>
          </AppCard>
        </div>
      </div>
    </AppShell>
  );
}
