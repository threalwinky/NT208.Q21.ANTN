"use client";

import {
  BarChart3,
  BookText,
  BotMessageSquare,
  ChevronDown,
  ChevronUp,
  Music4,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import {
  createMoodCheckin,
  createWellbeingCheckin,
  getEnergyInsight,
  getMoodJournals,
  getMoods,
  getSupportResources,
  getWellbeingCheckins,
  getWellbeingMusic,
  getChatSessions,
  previewEnergyInsight,
  type EnergyInsight,
  type MoodJournal,
  type MusicTrack,
  type WellbeingCheckin,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";

// ── Hằng số ───────────────────────────────────────────────────────────────────

const JOURNAL_PREVIEW_COUNT = 4;

const TABS = [
  { key: "diary", label: "Nhật ký", icon: BookText },
  { key: "checkin", label: "Check-in", icon: BarChart3 },
  { key: "music", label: "Nhạc theo mood", icon: Music4 },
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

// ── Kiểu nội bộ ───────────────────────────────────────────────────────────────

type ChatSessionRaw = {
  id: number;
  updated_at?: string;
  messages?: Array<{ role: string; content: string; created_at: string }>;
};

// ── Trang chính ───────────────────────────────────────────────────────────────

export default function DiaryPage() {
  const [tab, setTab] = useState<TabKey>("diary");
  const initRef = useRef(false);

  // đọc ?tab= từ URL khi load lần đầu
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tab") as TabKey | null;
    if (t && TABS.some((item) => item.key === t)) setTab(t);
  }, []);

  // ── Nhật ký ────────────────────────────────────────────────────────────────
  const [moods, setMoods] = useState<Array<Record<string, unknown>>>([]);
  const [journals, setJournals] = useState<MoodJournal[]>([]);
  const [resources, setResources] = useState<Array<Record<string, unknown>>>([]);
  const [insight, setInsight] = useState<EnergyInsight | null>(null);
  const [selectedMood, setSelectedMood] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [showAllJournals, setShowAllJournals] = useState(false);
  const [isInsightRefreshing, setIsInsightRefreshing] = useState(false);
  const [pageError, setPageError] = useState("");

  // ── Check-in ───────────────────────────────────────────────────────────────
  const [checkinForm, setCheckinForm] = useState<Record<string, string | number>>(CHECKIN_DEFAULTS);
  const [checkins, setCheckins] = useState<WellbeingCheckin[]>([]);

  // ── Nhạc ──────────────────────────────────────────────────────────────────
  const [musicTheme, setMusicTheme] = useState("calm");
  const [tracks, setTracks] = useState<MusicTrack[]>([]);

  // ── Phân tích từ chatbot ──────────────────────────────────────────────────
  const [chatInsight, setChatInsight] = useState<EnergyInsight | null>(null);
  const [chatInsightLoading, setChatInsightLoading] = useState(false);
  const [chatContext, setChatContext] = useState<string>(""); // trích đoạn tin nhắn gốc

  // ── Tải dữ liệu ban đầu ───────────────────────────────────────────────────

  async function refreshDiary() {
    setPageError("");
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
      const preferred = moodData.find(
        (item) => String(item.display_name) === String(insightData.latest_mood_label ?? ""),
      );
      setSelectedMood(Number(preferred?.id ?? moodData[0].id));
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setPageError("");
        const [moodData, journalData, resourceData, insightData] = await Promise.all([
          getMoods(),
          getMoodJournals(),
          getSupportResources(),
          getEnergyInsight(),
        ]);
        if (!mounted) return;
        setMoods(moodData);
        setJournals(journalData);
        setResources(resourceData);
        setInsight(insightData);
        if (moodData[0]?.id) {
          const preferred = moodData.find(
            (item) => String(item.display_name) === String(insightData.latest_mood_label ?? ""),
          );
          setSelectedMood((current) => current ?? Number(preferred?.id ?? moodData[0].id));
        }
      } catch (caughtError) {
        if (mounted)
          setPageError(
            caughtError instanceof Error ? caughtError.message : "Không tải được dữ liệu nhật ký.",
          );
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  // Cập nhật insight khi người dùng đổi mood / note thủ công
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

  // Tải check-in
  useEffect(() => {
    getWellbeingCheckins().then(setCheckins);
  }, []);

  // Tải nhạc theo theme
  useEffect(() => {
    getWellbeingMusic(musicTheme).then(setTracks);
  }, [musicTheme]);

  // ── Phân tích cảm xúc từ hội thoại chatbot ───────────────────────────────

  async function analyzeChatMood() {
    setChatInsightLoading(true);
    try {
      const rawSessions = (await getChatSessions()) as ChatSessionRaw[];
      if (rawSessions.length === 0) return;

      // Lấy phiên gần nhất (đã sort theo updated_at ở API)
      const lastSession = rawSessions[0];
      const messages = (lastSession.messages ?? [])
        .filter((m) => m.role === "user")
        .slice(-6); // tối đa 6 tin nhắn gần nhất của người dùng

      if (messages.length === 0) return;

      const combinedText = messages.map((m) => m.content).join(" | ");
      setChatContext(combinedText.slice(0, 200) + (combinedText.length > 200 ? "..." : ""));

      // Gửi nội dung hội thoại vào hàm phân tích insight
      const preview = await previewEnergyInsight({ short_note: combinedText.slice(0, 600) });
      setChatInsight(preview);

      // Tự động áp dụng theme nhạc phù hợp với mood phát hiện được
      setMusicTheme(preview.music_theme || "calm");
    } catch {
      // Không báo lỗi — đây là tính năng bổ sung, không bắt buộc
    } finally {
      setChatInsightLoading(false);
    }
  }

  useEffect(() => {
    void analyzeChatMood();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Áp dụng gợi ý từ chatbot vào nhật ký thủ công
  function applyChatInsight() {
    if (!chatInsight || moods.length === 0) return;
    const detectedLabel = chatInsight.latest_mood_label ?? "";
    const matched = moods.find(
      (m) => String(m.display_name).toLowerCase() === detectedLabel.toLowerCase(),
    );
    if (matched) setSelectedMood(Number(matched.id));
    if (chatContext) setNote(chatContext.replace(/\s*\|\s*/g, " ").trim());
  }

  // ── Dữ liệu hiển thị ──────────────────────────────────────────────────────
  const visibleJournals = showAllJournals ? journals : journals.slice(0, JOURNAL_PREVIEW_COUNT);
  const hasHiddenJournals = journals.length > JOURNAL_PREVIEW_COUNT;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <AppShell
      pageTitle="Nhật ký"
      pageDescription="Ghi nhật ký cảm xúc, check-in hàng ngày và nghe nhạc theo mood."
    >
      {/* Tab bar */}
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

      {/* ═══════════════════════════ TAB: NHẬT KÝ ═══════════════════════════ */}
      {tab === "diary" && (
        <>
          {pageError ? (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
              {pageError}
            </div>
          ) : null}

          {/* Phân tích từ chatbot */}
          <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--text-primary)]">
                <BotMessageSquare className="h-4 w-4 text-[color:var(--accent)]" />
                Tín hiệu từ hội thoại gần nhất
              </div>
              <button
                type="button"
                onClick={() => void analyzeChatMood()}
                disabled={chatInsightLoading}
                className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--line)] px-3 py-1 text-xs text-[color:var(--text-muted)] transition hover:border-[color:var(--accent)]/30 hover:text-[color:var(--accent)] disabled:opacity-50"
              >
                <RefreshCw className={`h-3 w-3 ${chatInsightLoading ? "animate-spin" : ""}`} />
                {chatInsightLoading ? "Đang phân tích..." : "Cập nhật"}
              </button>
            </div>

            {chatInsightLoading && !chatInsight ? (
              <p className="mt-3 text-sm text-[color:var(--text-muted)]">
                Studify đang đọc hội thoại gần nhất để nhận diện mood của bạn...
              </p>
            ) : chatInsight ? (
              <div className="mt-3 space-y-3">
                {/* Trích đoạn context */}
                {chatContext ? (
                  <p className="line-clamp-2 text-sm italic leading-6 text-[color:var(--text-muted)]">
                    "{chatContext}"
                  </p>
                ) : null}
                {/* Nhãn mood + tín hiệu */}
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="accent">{chatInsight.latest_mood_label ?? "Không rõ"}</Badge>
                  <Badge tone="default">Năng lượng {chatInsight.latest_energy_level}/5</Badge>
                  {(chatInsight.signals ?? []).slice(0, 3).map((s) => (
                    <Badge key={s} tone="default">
                      {s}
                    </Badge>
                  ))}
                </div>
                {/* Tóm tắt */}
                <p className="text-sm leading-6 text-[color:var(--text-primary)]">{chatInsight.summary}</p>
                {/* Nút áp dụng */}
                <button
                  type="button"
                  onClick={applyChatInsight}
                  className="inline-flex items-center gap-2 rounded-md bg-[color:var(--accent-soft)] px-4 py-2 text-sm font-medium text-[color:var(--accent)] transition hover:bg-[color:var(--accent)] hover:text-white"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Áp dụng vào nhật ký hôm nay
                </button>
              </div>
            ) : (
              <p className="mt-3 text-sm text-[color:var(--text-muted)]">
                Chưa có hội thoại nào để phân tích. Hãy chat với Studify một chút rồi quay lại đây.
              </p>
            )}
          </div>

          {/* Nội dung nhật ký */}
          <div className="grid gap-4 xl:grid-cols-[0.82fr_1.18fr]">
            <AppCard
              title="Hôm nay bạn thế nào?"
              subtitle="Chọn tâm trạng gần nhất rồi viết vài dòng ngắn. Năng lượng sẽ được phân tích tự động."
            >
              <div className="grid gap-3 sm:grid-cols-2">
                {moods.map((item) => (
                  <button
                    key={String(item.id)}
                    type="button"
                    onClick={() => setSelectedMood(Number(item.id))}
                    className={`rounded-lg border p-4 text-left transition ${
                      selectedMood === Number(item.id)
                        ? "border-transparent bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                        : "border-[color:var(--line)] bg-[color:var(--surface-soft)] hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                    }`}
                  >
                    <p className="font-medium">{String(item.display_name)}</p>
                    <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                      {String(item.description ?? "Một nhịp cảm xúc trong ngày.")}
                    </p>
                  </button>
                ))}
              </div>
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                className="mt-4 min-h-[120px] w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm leading-6 outline-none"
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
                  await refreshDiary();
                }}
                className="btn-primary mt-4 rounded-lg px-5 py-3 text-sm font-semibold transition"
              >
                Lưu nhật ký hôm nay
              </button>
            </AppCard>

            <div className="space-y-4">
              {/* Số liệu tóm tắt */}
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-sm">
                  <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                    <BarChart3 className="h-4 w-4 text-[color:var(--accent)]" />
                    Năng lượng
                  </div>
                  <p className="mt-3 text-3xl font-semibold tracking-tight">
                    {insight?.latest_energy_level ?? 3}/5
                  </p>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                    {insight?.latest_energy_label ?? "Trung bình"}
                  </p>
                </div>
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-sm">
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
                  <p className="mt-3 text-3xl font-semibold tracking-tight">
                    {insight?.average_energy_level ?? 3}
                  </p>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                    {insight?.trend === "DOWN"
                      ? "Đang chùng xuống"
                      : insight?.trend === "UP"
                        ? "Đang lên"
                        : "Ổn định"}
                  </p>
                </div>
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-sm">
                  <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
                    <Music4 className="h-4 w-4 text-[color:var(--accent)]" />
                    Gợi ý
                  </div>
                  <p className="mt-3 text-lg font-semibold">
                    {insight?.music_theme_label ?? "Nhạc gợi ý"}
                  </p>
                  <p className="mt-2 text-sm text-[color:var(--text-muted)]">{insight?.summary}</p>
                </div>
              </div>

              {/* Phân tích nhịp */}
              <AppCard
                title="Phân tích nhịp gần nhất"
                subtitle="Studify đọc từ tâm trạng và vài cụm trong nhật ký để ước lượng mức năng lượng hiện tại."
              >
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="accent">{insight?.latest_mood_label ?? "Chưa có tâm trạng"}</Badge>
                    <Badge tone="default">{insight?.latest_energy_label ?? "Trung bình"}</Badge>
                    {(insight?.signals ?? []).map((signal) => (
                      <Badge key={signal} tone="default">
                        {signal}
                      </Badge>
                    ))}
                  </div>
                  <p className="mt-4 text-sm leading-6 text-[color:var(--text-primary)]">
                    {insight?.summary}
                  </p>
                </div>
              </AppCard>

              {/* Bài hát gợi ý từ insight thủ công */}
              <AppCard
                title="Bài hát gợi ý"
                subtitle={
                  isInsightRefreshing
                    ? "Đang đổi vibe theo mood hiện tại..."
                    : "Studify chọn theo mood bạn chọn tay hoặc từ hội thoại gần nhất."
                }
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
                        className="block h-[152px] w-full overflow-hidden rounded-md"
                        style={{ border: 0 }}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5 text-sm text-[color:var(--text-muted)]">
                    Chưa lấy được danh sách bài hát ở lần này. Lưu một dòng ngắn rồi tải lại để Studify
                    chọn lại vibe.
                  </div>
                )}
              </AppCard>

              {/* Nhật ký gần đây */}
              <AppCard
                title="Nhật ký gần đây"
                subtitle="Nhìn lại vài dòng gần nhất để xem tuần này bạn đang dồn vào đâu."
              >
                <div className="space-y-3">
                  {visibleJournals.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-medium">{item.mood_label ?? "Nhật ký"}</p>
                        <Badge tone="accent">
                          {item.energy_label} • {item.energy_level}/5
                        </Badge>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">
                        {item.short_note ?? ""}
                      </p>
                      <p className="mt-2 text-sm text-[color:var(--text-muted)]">{item.energy_summary}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.signals.map((signal) => (
                          <Badge key={signal} tone="default">
                            {signal}
                          </Badge>
                        ))}
                      </div>
                      <p className="mt-4 text-sm text-[color:var(--text-soft)]">
                        {formatDateTime(item.created_at)}
                      </p>
                    </div>
                  ))}
                  {hasHiddenJournals ? (
                    <button
                      type="button"
                      onClick={() => setShowAllJournals((current) => !current)}
                      className="btn-secondary inline-flex items-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition"
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

              {/* Nguồn hỗ trợ */}
              <AppCard
                title="Nguồn hỗ trợ trong trường"
                subtitle="Các kênh để bạn tìm thêm một điểm chạm nhẹ khi đang cần sắp xếp lại."
              >
                <div className="space-y-3">
                  {resources.map((item) => (
                    <a
                      key={String(item.id)}
                      href={String(item.link_url ?? "#")}
                      target="_blank"
                      rel="noreferrer"
                      className="block rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4 transition hover:border-[color:var(--accent)]/25 hover:bg-[color:var(--accent-soft)]"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium">{String(item.title)}</p>
                          <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                            {String(item.description ?? "")}
                          </p>
                        </div>
                        <Badge tone={Boolean(item.is_official_uit) ? "success" : "warn"}>
                          {String(item.resource_type)}
                        </Badge>
                      </div>
                      <p className="mt-4 text-sm text-[color:var(--text-soft)]">
                        {String(item.owner_unit ?? "")}
                      </p>
                    </a>
                  ))}
                </div>
              </AppCard>
            </div>
          </div>
        </>
      )}

      {/* ═════════════════════════ TAB: CHECK-IN ═════════════════════════════ */}
      {tab === "checkin" && (
        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <AppCard title="Check-in mới" subtitle="Thang 1-5, chọn gần đúng là đủ.">
            <label className="block">
              <span className="text-sm text-[color:var(--text-muted)]">Mood code</span>
              <input
                value={String(checkinForm.mood_code)}
                onChange={(event) =>
                  setCheckinForm((current) => ({ ...current, mood_code: event.target.value }))
                }
                className="mt-2 w-full rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </label>
            <div className="mt-4 space-y-4">
              {CHECKIN_SLIDERS.map((key) => (
                <label
                  key={key}
                  className="block rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4"
                >
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize text-[color:var(--text-muted)]">
                      {key.replace("_", " ")}
                    </span>
                    <span className="font-semibold">{String(checkinForm[key])}/5</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={5}
                    value={Number(checkinForm[key])}
                    onChange={(event) =>
                      setCheckinForm((current) => ({
                        ...current,
                        [key]: Number(event.target.value),
                      }))
                    }
                    className="mt-3 w-full"
                  />
                </label>
              ))}
            </div>
            <textarea
              value={String(checkinForm.note_preview)}
              onChange={(event) =>
                setCheckinForm((current) => ({ ...current, note_preview: event.target.value }))
              }
              className="mt-4 min-h-[110px] w-full rounded-md border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              placeholder="Một dòng ngắn nếu muốn..."
            />
            <button
              type="button"
              onClick={async () => {
                await createWellbeingCheckin(checkinForm);
                setCheckinForm(CHECKIN_DEFAULTS);
                setCheckins(await getWellbeingCheckins());
              }}
              className="btn-primary mt-4 rounded-lg px-5 py-3 text-sm font-semibold transition"
            >
              Lưu check-in
            </button>
          </AppCard>

          <AppCard title="Check-in gần đây" subtitle="Dữ liệu này riêng tư theo tài khoản sinh viên.">
            <div className="space-y-3">
              {checkins.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="accent">{item.mood_code}</Badge>
                    <Badge tone="default">Energy {item.energy}/5</Badge>
                    <Badge tone={item.stress >= 4 ? "warn" : "default"}>Stress {item.stress}/5</Badge>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">
                    {item.note_preview ?? "Không có ghi chú."}
                  </p>
                  <p className="mt-2 text-xs text-[color:var(--text-soft)]">
                    {formatDateTime(item.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </AppCard>
        </div>
      )}

      {/* ═══════════════════════ TAB: NHẠC THEO MOOD ═════════════════════════ */}
      {tab === "music" && (
        <>
          {/* Card: gợi ý từ chatbot */}
          <div className="rounded-lg border border-[color:var(--accent)]/30 bg-[color:var(--accent-soft)] p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--accent)]">
              <BotMessageSquare className="h-4 w-4" />
              Gợi ý từ hội thoại chatbot
            </div>

            {chatInsightLoading && !chatInsight ? (
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                Đang phân tích hội thoại gần nhất...
              </p>
            ) : chatInsight ? (
              <div className="mt-3 space-y-2">
                {chatContext ? (
                  <p className="line-clamp-2 text-xs italic leading-5 text-[color:var(--text-muted)]">
                    "{chatContext}"
                  </p>
                ) : null}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-[color:var(--text-primary)]">Mood phát hiện:</span>
                  <Badge tone="accent">{chatInsight.latest_mood_label ?? "Không rõ"}</Badge>
                  <span className="text-sm text-[color:var(--text-primary)]">→ Playlist đề xuất:</span>
                  <Badge tone="accent">{chatInsight.music_theme_label}</Badge>
                </div>
                <p className="text-sm leading-6 text-[color:var(--text-primary)]">{chatInsight.summary}</p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                Chưa có hội thoại để phân tích. Chat với Studify trước nhé!
              </p>
            )}

            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                onClick={() => void analyzeChatMood()}
                disabled={chatInsightLoading}
                className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--accent)]/30 bg-[color:var(--surface)] px-3 py-1 text-xs text-[color:var(--accent)] transition hover:bg-[color:var(--accent)] hover:text-white disabled:opacity-50"
              >
                <RefreshCw className={`h-3 w-3 ${chatInsightLoading ? "animate-spin" : ""}`} />
                Phân tích lại
              </button>
            </div>
          </div>

          {/* Card: chọn vibe thủ công */}
          <AppCard
            title="Đổi vibe thủ công"
            subtitle="Studify đổi danh sách theo theme bạn chọn. Theme đang active được tô sáng."
          >
            <div className="flex flex-wrap gap-2">
              {MUSIC_THEMES.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMusicTheme(value)}
                  className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                    musicTheme === value
                      ? "border-transparent bg-[color:var(--accent)] text-white"
                      : "border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-muted)] hover:border-[color:var(--accent)]/30 hover:text-[color:var(--accent)]"
                  }`}
                >
                  {label}
                  {chatInsight?.music_theme === value ? (
                    <span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current opacity-70" />
                  ) : null}
                </button>
              ))}
            </div>
            {chatInsight ? (
              <p className="mt-3 text-xs text-[color:var(--text-soft)]">
                • = theme Studify đề xuất dựa trên hội thoại gần nhất
              </p>
            ) : null}
          </AppCard>

          {/* Spotify embeds */}
          <AppCard
            title="Playlist đang phát"
            subtitle="Nếu Spotify API tắt hoặc thiếu token, hệ thống tự dùng danh sách curated trong backend."
          >
            <div className="grid gap-4 xl:grid-cols-2">
              {tracks.map((track) => (
                <div
                  key={track.embed_url}
                  className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-3"
                >
                  <div className="mb-3 flex items-center gap-2">
                    <Badge tone="accent">{track.artist}</Badge>
                    <span className="text-sm font-medium">{track.title}</span>
                  </div>
                  <iframe
                    title={`${track.title} - ${track.artist}`}
                    src={track.embed_url}
                    loading="lazy"
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    className="block h-[152px] w-full overflow-hidden rounded-md"
                    style={{ border: 0 }}
                  />
                </div>
              ))}
            </div>
          </AppCard>
        </>
      )}
    </AppShell>
  );
}
