"use client";

import { BarChart3, BookText, ChevronDown, ChevronUp, Music4, NotebookPen, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import {
  createMoodCheckin,
  createWellbeingCheckin,
  createWellbeingNote,
  deleteWellbeingNote,
  getEnergyInsight,
  getMoodJournals,
  getMoods,
  getSupportResources,
  getWellbeingCheckins,
  getWellbeingMusic,
  getWellbeingNotes,
  previewEnergyInsight,
  type EnergyInsight,
  type MoodJournal,
  type MusicTrack,
  type WellbeingCheckin,
  type WellbeingNote,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const JOURNAL_PREVIEW_COUNT = 4;

const TABS = [
  { key: "diary", label: "Nhật ký", icon: BookText },
  { key: "checkin", label: "Check-in", icon: BarChart3 },
  { key: "music", label: "Nhạc theo mood", icon: Music4 },
  { key: "notes", label: "Ghi chú riêng", icon: NotebookPen },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const MUSIC_THEMES: [string, string][] = [
  ["focus", "Tập trung"],
  ["calm", "Chill"],
  ["upbeat", "Nâng mood"],
  ["love", "Dễ chịu"],
];

const CHECKIN_SLIDERS = ["valence", "energy", "stress", "motivation", "focus", "sleep_quality"];
const CHECKIN_DEFAULTS: Record<string, string | number> = {
  mood_code: "neutral",
  valence: 3,
  energy: 3,
  stress: 3,
  motivation: 3,
  focus: 3,
  sleep_quality: 3,
  note_preview: "",
};

export default function DiaryPage() {
  const [tab, setTab] = useState<TabKey>("diary");
  const initRef = useRef(false);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tab") as TabKey | null;
    if (t && TABS.some((item) => item.key === t)) setTab(t);
  }, []);

  // --- Nhật ký state ---
  const [moods, setMoods] = useState<Array<Record<string, unknown>>>([]);
  const [journals, setJournals] = useState<MoodJournal[]>([]);
  const [resources, setResources] = useState<Array<Record<string, unknown>>>([]);
  const [insight, setInsight] = useState<EnergyInsight | null>(null);
  const [selectedMood, setSelectedMood] = useState<number | null>(null);
  const [note, setNote] = useState("Hơi mệt vì deadline dồn nhưng vẫn muốn sắp xếp lại.");
  const [showAllJournals, setShowAllJournals] = useState(false);
  const [isInsightRefreshing, setIsInsightRefreshing] = useState(false);
  const [pageError, setPageError] = useState("");

  // --- Check-in state ---
  const [checkinForm, setCheckinForm] = useState<Record<string, string | number>>(CHECKIN_DEFAULTS);
  const [checkins, setCheckins] = useState<WellbeingCheckin[]>([]);

  // --- Music state ---
  const [musicTheme, setMusicTheme] = useState("focus");
  const [tracks, setTracks] = useState<MusicTrack[]>([]);

  // --- Notes state ---
  const [notes, setNotes] = useState<WellbeingNote[]>([]);
  const [noteTitle, setNoteTitle] = useState("Ghi chú riêng");
  const [noteContent, setNoteContent] = useState("Hôm nay mình muốn viết vài dòng để gỡ rối việc học.");

  async function refreshDiary() {
    setPageError("");
    const [moodData, journalData, resourceData, insightData] = await Promise.all([getMoods(), getMoodJournals(), getSupportResources(), getEnergyInsight()]);
    setMoods(moodData);
    setJournals(journalData);
    setResources(resourceData);
    setInsight(insightData);
    if (!selectedMood && moodData[0]?.id) {
      const preferred = moodData.find((item) => String(item.display_name) === String(insightData.latest_mood_label ?? ""));
      setSelectedMood(Number(preferred?.id ?? moodData[0].id));
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setPageError("");
        const [moodData, journalData, resourceData, insightData] = await Promise.all([getMoods(), getMoodJournals(), getSupportResources(), getEnergyInsight()]);
        if (!mounted) return;
        setMoods(moodData);
        setJournals(journalData);
        setResources(resourceData);
        setInsight(insightData);
        if (moodData[0]?.id) {
          const preferred = moodData.find((item) => String(item.display_name) === String(insightData.latest_mood_label ?? ""));
          setSelectedMood((current) => current ?? Number(preferred?.id ?? moodData[0].id));
        }
      } catch (caughtError) {
        if (mounted) setPageError(caughtError instanceof Error ? caughtError.message : "Không tải được dữ liệu nhật ký.");
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedMood) return;
    let active = true;
    const timer = window.setTimeout(async () => {
      setIsInsightRefreshing(true);
      try {
        const preview = await previewEnergyInsight({ mood_state_id: selectedMood, short_note: note });
        if (active) setInsight(preview);
      } finally {
        if (active) setIsInsightRefreshing(false);
      }
    }, 320);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [selectedMood, note]);

  useEffect(() => {
    getWellbeingCheckins().then(setCheckins);
  }, []);

  useEffect(() => {
    getWellbeingMusic(musicTheme).then(setTracks);
  }, [musicTheme]);

  useEffect(() => {
    getWellbeingNotes().then(setNotes);
  }, []);

  const visibleJournals = showAllJournals ? journals : journals.slice(0, JOURNAL_PREVIEW_COUNT);
  const hasHiddenJournals = journals.length > JOURNAL_PREVIEW_COUNT;

  return (
    <AppShell pageTitle="Nhật ký" pageDescription="Ghi nhật ký cảm xúc, check-in hàng ngày, nghe nhạc theo mood và lưu ghi chú riêng tư.">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
              tab === key
                ? "bg-[color:var(--accent)] text-white"
                : "border border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-muted)] hover:border-[color:var(--accent)]/30 hover:text-[color:var(--text-primary)]"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "diary" && (
        <>
          {pageError ? (
            <div className="mb-4 rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">{pageError}</div>
          ) : null}
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
                  await createMoodCheckin({ mood_state_id: selectedMood, short_note: note, needs_human_support: false });
                  await refreshDiary();
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
                </div>
              </AppCard>

              <AppCard
                title="Bài hát gợi ý"
                subtitle={isInsightRefreshing ? "Đang đổi vibe theo mood hiện tại..." : "Studify chọn ngẫu nhiên theo mood hiện tại của bạn và hiển thị trực tiếp bằng Spotify embed."}
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
                          <ChevronUp className="h-4 w-4" />
                          Thu gọn
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-4 w-4" />
                          Xem thêm
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
        </>
      )}

      {tab === "checkin" && (
        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <AppCard title="Check-in mới" subtitle="Thang 1-5, chọn gần đúng là đủ.">
            <label className="block">
              <span className="text-sm text-[color:var(--text-muted)]">Mood code</span>
              <input
                value={String(checkinForm.mood_code)}
                onChange={(event) => setCheckinForm((current) => ({ ...current, mood_code: event.target.value }))}
                className="mt-2 w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </label>
            <div className="mt-4 space-y-4">
              {CHECKIN_SLIDERS.map((key) => (
                <label key={key} className="block rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize text-[color:var(--text-muted)]">{key.replace("_", " ")}</span>
                    <span className="font-semibold">{String(checkinForm[key])}/5</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={5}
                    value={Number(checkinForm[key])}
                    onChange={(event) => setCheckinForm((current) => ({ ...current, [key]: Number(event.target.value) }))}
                    className="mt-3 w-full"
                  />
                </label>
              ))}
            </div>
            <textarea
              value={String(checkinForm.note_preview)}
              onChange={(event) => setCheckinForm((current) => ({ ...current, note_preview: event.target.value }))}
              className="mt-4 min-h-[110px] w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              placeholder="Một dòng ngắn nếu muốn..."
            />
            <button
              type="button"
              onClick={async () => {
                await createWellbeingCheckin(checkinForm);
                setCheckinForm(CHECKIN_DEFAULTS);
                setCheckins(await getWellbeingCheckins());
              }}
              className="btn-primary mt-4 rounded-2xl px-5 py-3 text-sm font-semibold transition"
            >
              Lưu check-in
            </button>
          </AppCard>
          <AppCard title="Check-in gần đây" subtitle="Dữ liệu này riêng tư theo tài khoản sinh viên.">
            <div className="space-y-3">
              {checkins.map((item) => (
                <div key={item.id} className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="accent">{item.mood_code}</Badge>
                    <Badge tone="default">Energy {item.energy}/5</Badge>
                    <Badge tone={item.stress >= 4 ? "warn" : "default"}>Stress {item.stress}/5</Badge>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">{item.note_preview ?? "Không có ghi chú."}</p>
                  <p className="mt-2 text-xs text-[color:var(--text-soft)]">{formatDateTime(item.created_at)}</p>
                </div>
              ))}
            </div>
          </AppCard>
        </div>
      )}

      {tab === "music" && (
        <>
          <AppCard title="Chọn vibe" subtitle="Studify đổi danh sách theo theme mà không cần lưu dữ liệu nhạy cảm.">
            <div className="flex flex-wrap gap-2">
              {MUSIC_THEMES.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMusicTheme(value)}
                  className={`rounded-full border px-4 py-2 text-sm transition ${musicTheme === value ? "border-transparent bg-[color:var(--accent)] text-white" : "border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-muted)]"}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </AppCard>
          <AppCard title="Spotify embed" subtitle="Nếu Spotify API tắt hoặc thiếu token, hệ thống tự dùng danh sách curated trong backend.">
            <div className="grid gap-4 xl:grid-cols-2">
              {tracks.map((track) => (
                <div key={track.embed_url} className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-3">
                  <div className="mb-3 flex items-center gap-2">
                    <Badge tone="accent">{track.artist}</Badge>
                    <span className="text-sm font-medium">{track.title}</span>
                  </div>
                  <iframe
                    title={`${track.title} - ${track.artist}`}
                    src={track.embed_url}
                    loading="lazy"
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    className="block h-[152px] w-full overflow-hidden rounded-[18px]"
                    style={{ border: 0 }}
                  />
                </div>
              ))}
            </div>
          </AppCard>
        </>
      )}

      {tab === "notes" && (
        <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
          <AppCard title="Viết ghi chú" subtitle="Nội dung không tự động gửi sang LLM để giữ riêng tư.">
            <input
              value={noteTitle}
              onChange={(event) => setNoteTitle(event.target.value)}
              className="w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
            />
            <textarea
              value={noteContent}
              onChange={(event) => setNoteContent(event.target.value)}
              className="mt-4 min-h-[220px] w-full rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm leading-6 outline-none"
            />
            <button
              type="button"
              onClick={async () => {
                await createWellbeingNote({ title: noteTitle, content: noteContent, mood_code: "neutral" });
                setNoteContent("");
                setNotes(await getWellbeingNotes());
              }}
              className="btn-primary mt-4 rounded-2xl px-5 py-3 text-sm font-semibold transition"
            >
              Lưu ghi chú
            </button>
          </AppCard>
          <AppCard title="Ghi chú đã lưu" subtitle="Danh sách gần đây trong tài khoản của bạn.">
            <div className="space-y-3">
              {notes.map((item) => (
                <div key={item.id} className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Badge tone="success">Private</Badge>
                      <p className="mt-3 font-medium">{item.title}</p>
                    </div>
                    <button
                      type="button"
                      onClick={async () => {
                        await deleteWellbeingNote(item.id);
                        setNotes(await getWellbeingNotes());
                      }}
                      className="rounded-full border border-[color:var(--line)] px-3 py-1 text-xs text-[color:var(--text-muted)]"
                    >
                      Xóa
                    </button>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[color:var(--text-primary)]">{item.content}</p>
                  <p className="mt-3 text-xs text-[color:var(--text-soft)]">{formatDateTime(item.created_at)}</p>
                </div>
              ))}
            </div>
          </AppCard>
        </div>
      )}
    </AppShell>
  );
}
