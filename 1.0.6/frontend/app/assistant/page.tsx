"use client";

import {
  AlertTriangle,
  AudioLines,
  Check,
  Copy,
  ExternalLink,
  Globe,
  Heart,
  Keyboard,
  MessageCircleHeart,
  Mic,
  MicOff,
  Phone,
  Plus,
  Send,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { MarkdownContent } from "@/components/markdown-content";
import {
  deleteChatSession,
  getChatSessions,
  sendFeedback,
  streamChatMessage,
  type ChatReply,
  type CitationItem,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";

// ── Kiểu dữ liệu ─────────────────────────────────────────────────────────────

type ChatMessage = {
  id: number;
  role: string;
  category?: string | null;
  content: string;
  created_at: string;
};

type SessionItem = {
  id: number;
  title: string;
  mode: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

type StreamingReply = Omit<ChatReply, "answer"> & { answer: string };

// ── Hằng số ───────────────────────────────────────────────────────────────────

/** Từ khóa/cụm từ gợi ý nguy cơ cao — dùng để kích hoạt safety banner */
const CRISIS_KEYWORDS = [
  "tự tử", "muốn chết", "không muốn sống", "muốn biến mất",
  "kết thúc tất cả", "không muốn tiếp tục", "chán sống",
  "không ai cần mình", "không muốn ở đây nữa",
  "không còn cách nào", "hại bản thân", "tự làm đau",
  "muốn mất đi", "không thấy lối ra", "vô nghĩa mãi",
];

const starterPrompts = [
  "Tuần này có thông báo học vụ gì?",
  "Cách xin giấy xác nhận sinh viên?",
  "Mình hơi áp lực vì deadline dồn.",
  "Giúp mình sắp lại tuần này.",
];

// Chế độ tương tác: Text (gõ + đọc) hoặc Voice (nói + nghe Studify đọc).
type InputMode = "text" | "voice";

const INPUT_MODES: Array<{ id: InputMode; label: string; hint: string; icon: typeof Keyboard }> = [
  { id: "text", label: "Text", hint: "Gõ và đọc câu trả lời", icon: Keyboard },
  { id: "voice", label: "Voice", hint: "Nói với Studify, nghe Studify trả lời bằng giọng", icon: AudioLines },
];

// ── Text-to-Speech (Studify đọc câu trả lời ở chế độ Voice) ──────────────────
function stripForSpeech(text: string): string {
  return (text || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1") // [label](url) -> label
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/[#>*_`~|-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function speakText(text: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  try {
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(stripForSpeech(text).slice(0, 2000));
    utterance.lang = "vi-VN";
    utterance.rate = 1.0;
    const viVoice = synth.getVoices().find((v) => v.lang?.toLowerCase().startsWith("vi"));
    if (viVoice) utterance.voice = viVoice;
    synth.speak(utterance);
  } catch {
    /* trình duyệt không hỗ trợ -> bỏ qua */
  }
}

function stopSpeaking() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    try {
      window.speechSynthesis.cancel();
    } catch {
      /* noop */
    }
  }
}

// ── Tiện ích ──────────────────────────────────────────────────────────────────

function sortSessions(items: SessionItem[]) {
  return [...items].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

function sortMessages(messages: ChatMessage[]) {
  return [...messages].sort((a, b) => {
    const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return diff !== 0 ? diff : a.id - b.id;
  });
}

/**
 * Gom sessions thành 3 nhóm: Hôm nay / Tuần này / Cũ hơn
 */
function groupSessions(sessions: SessionItem[]) {
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

  const today: SessionItem[] = [];
  const thisWeek: SessionItem[] = [];
  const older: SessionItem[] = [];

  for (const s of sessions) {
    const t = new Date(s.updated_at);
    if (t >= todayStart) today.push(s);
    else if (t >= weekAgo) thisWeek.push(s);
    else older.push(s);
  }

  return [
    ...(today.length > 0 ? [{ label: "Hôm nay", items: today }] : []),
    ...(thisWeek.length > 0 ? [{ label: "Tuần này", items: thisWeek }] : []),
    ...(older.length > 0 ? [{ label: "Cũ hơn", items: older }] : []),
  ];
}

/**
 * Tạo tiêu đề session tốt hơn: lấy câu đầu tiên, cắt tại ranh giới từ nếu dài quá
 */
function generateTitle(prompt: string): string {
  const firstLine = prompt.split("\n")[0]?.trim() ?? prompt;
  const firstSentence = firstLine.split(/[.!?。]/)[0]?.trim() ?? firstLine;
  if (firstSentence.length > 0 && firstSentence.length <= 72) return firstSentence;
  const words = firstSentence.split(" ");
  let title = "";
  for (const word of words) {
    const candidate = title ? `${title} ${word}` : word;
    if (candidate.length > 62) break;
    title = candidate;
  }
  return title ? `${title}…` : firstSentence.slice(0, 62) + "…";
}

function detectCrisis(text: string): boolean {
  const lower = text.toLowerCase();
  return CRISIS_KEYWORDS.some((kw) => lower.includes(kw));
}

// ── Sub-components ────────────────────────────────────────────────────────────

function AssistantStatusHeader({ status }: { status: string }) {
  if (status.startsWith("web_search:")) {
    const query = status.slice("web_search:".length).trim();
    return (
      <div className="mb-2 flex items-center gap-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-blue-300 bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 dark:border-blue-400/20 dark:bg-blue-900/20 dark:text-blue-300">
          <Globe className="h-3.5 w-3.5 shrink-0 animate-spin" style={{ animationDuration: "1.8s" }} />
          <span className="shrink-0">Đang tìm kiếm web</span>
          {query ? (
            <span className="max-w-[240px] truncate border-l border-blue-300 pl-2 italic opacity-80 dark:border-blue-400/20">
              {query}
            </span>
          ) : null}
        </div>
      </div>
    );
  }
  if (status.startsWith("tool:")) {
    const name = status.slice("tool:".length).trim();
    return (
      <div className="mb-2 flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
        <MessageCircleHeart className="h-4 w-4 text-[color:var(--accent)]" />
        <span>Đang gọi công cụ: {name}</span>
      </div>
    );
  }
  return (
    <div className="mb-2 flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
      <MessageCircleHeart className="h-4 w-4 shrink-0 text-[color:var(--accent)]" />
      <span>{status}</span>
    </div>
  );
}

/** Banner an toàn — hiện khi phát hiện nội dung nguy cơ cao */
function WellbeingSafetyBanner({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 dark:border-rose-400/20 dark:bg-rose-400/8">
      <div className="flex items-start gap-3">
        <Heart className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-rose-700 dark:text-rose-300">
            Studify ở đây cùng bạn
          </p>
          <p className="mt-2 text-sm leading-6 text-rose-700/90 dark:text-rose-200/80">
            Mình thấy bạn đang nặng lòng. Điều đó hoàn toàn hợp lý — đôi khi áp lực dồn quá.
            Dưới đây là những chỗ bạn có thể tìm thêm một điểm chạm thật với người thật:
          </p>
          <div className="mt-4 space-y-2">
            <a
              href="https://ctsv.uit.edu.vn"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-4 py-2.5 text-sm font-medium text-rose-700 transition hover:bg-rose-50 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200"
            >
              <ExternalLink className="h-4 w-4 shrink-0" />
              Phòng Công tác Sinh viên UIT — ctsv.uit.edu.vn
            </a>
            <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-4 py-2.5 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
              <Phone className="h-4 w-4 shrink-0 text-rose-400" />
              <span>
                Đường dây hỗ trợ sức khỏe tâm thần 24/7 —{" "}
                <strong>1800 599 920</strong>{" "}
                <span className="opacity-70">(miễn phí)</span>
              </span>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <a
              href="https://ctsv.uit.edu.vn"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full bg-rose-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-rose-600"
            >
              <Heart className="h-4 w-4" />
              Tôi cần hỗ trợ ngay
            </a>
            <button
              type="button"
              onClick={onDismiss}
              className="text-sm text-rose-400 transition hover:text-rose-600"
            >
              Tiếp tục nhắn tin
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Citation cards nhỏ gọn dưới mỗi tin nhắn AI */
function CitationCards({ citations }: { citations: CitationItem[] }) {
  if (!citations.length) return null;
  return (
    <div className="mt-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[color:var(--text-soft)]">
        Nguồn tham khảo
      </p>
      <div className="flex flex-wrap gap-2">
        {citations.map((cite) => (
          <a
            key={cite.document_id}
            href={cite.url}
            target="_blank"
            rel="noreferrer"
            title={cite.excerpt}
            className="group flex max-w-[260px] items-start gap-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-xs transition hover:border-[color:var(--accent)]/40 hover:bg-[color:var(--accent-soft)]"
          >
            <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--text-soft)] group-hover:text-[color:var(--accent)]" />
            <div className="min-w-0">
              <p className="truncate font-medium text-[color:var(--text-primary)]">{cite.title}</p>
              <p className="text-[10px] text-[color:var(--text-muted)]">{cite.source_label}</p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/** Nút copy nội dung */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard không khả dụng */
    }
  }

  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      title="Sao chép"
      className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[color:var(--text-soft)] transition hover:bg-[color:var(--surface-strong)] hover:text-[color:var(--text-primary)]"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

/** Thumbs up / down feedback */
function MessageFeedback({
  messageId,
  sessionId,
  voted,
  onVote,
}: {
  messageId: number;
  sessionId: number;
  voted: "up" | "down" | null;
  onVote: (messageId: number, sessionId: number, rating: "up" | "down") => void;
}) {
  return (
    <div className="flex gap-0.5">
      <button
        type="button"
        onClick={() => onVote(messageId, sessionId, "up")}
        disabled={voted !== null}
        title="Hữu ích"
        className={`inline-flex h-7 w-7 items-center justify-center rounded-md transition ${
          voted === "up"
            ? "text-emerald-500"
            : "text-[color:var(--text-soft)] hover:bg-[color:var(--surface-strong)] hover:text-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        }`}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => onVote(messageId, sessionId, "down")}
        disabled={voted !== null}
        title="Chưa hữu ích"
        className={`inline-flex h-7 w-7 items-center justify-center rounded-md transition ${
          voted === "down"
            ? "text-rose-500"
            : "text-[color:var(--text-soft)] hover:bg-[color:var(--surface-strong)] hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-50"
        }`}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ── Khai báo kiểu Web Speech API ─────────────────────────────────────────────

interface ISpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: { transcript: string };
}

interface ISpeechRecognitionEvent extends Event {
  readonly results: ISpeechRecognitionResult[];
}

interface ISpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: ISpeechRecognitionEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

type SpeechRecognitionCtor = new () => ISpeechRecognition;

function getSpeechRecognitionClass(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as { SpeechRecognition?: SpeechRecognitionCtor }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor }).webkitSpeechRecognition ??
    null
  );
}

// ── Voice Input Hook ──────────────────────────────────────────────────────────

function useSpeechInput(onChange: (text: string) => void, onAutoSend?: (finalText: string) => void) {
  const [recording, setRecording] = useState(false);
  const [supported, setSupported] = useState(false);
  const recRef = useRef<ISpeechRecognition | null>(null);
  const baseRef = useRef("");
  const latestRef = useRef("");
  // luôn dùng callback mới nhất mà không cần tạo lại recognizer
  const autoSendRef = useRef(onAutoSend);
  autoSendRef.current = onAutoSend;

  useEffect(() => {
    setSupported(getSpeechRecognitionClass() !== null);
  }, []);

  function start(currentText: string) {
    const SRClass = getSpeechRecognitionClass();
    if (!SRClass) return;
    baseRef.current = currentText;
    latestRef.current = currentText;
    const rec = new SRClass();
    rec.lang = "vi-VN";
    rec.continuous = false;
    rec.interimResults = true;
    rec.onresult = (event: ISpeechRecognitionEvent) => {
      const transcript = Array.from({ length: event.results.length })
        .map((_, i) => event.results[i][0].transcript)
        .join("");
      const full = baseRef.current ? `${baseRef.current} ${transcript}` : transcript;
      latestRef.current = full;
      onChange(full);
    };
    rec.onerror = () => setRecording(false);
    rec.onend = () => {
      setRecording(false);
      // Chế độ Voice: dừng mic (hoặc nói xong) -> gửi luôn transcript cuối.
      const finalText = latestRef.current.trim();
      if (finalText) autoSendRef.current?.(finalText);
    };
    recRef.current = rec;
    rec.start();
    setRecording(true);
  }

  function stop() {
    recRef.current?.stop();
  }

  return { recording, supported, start, stop };
}

// ── Chat Composer ─────────────────────────────────────────────────────────────

function ChatComposer({
  content,
  loading,
  inputMode,
  onChange,
  onSubmit,
  onInputModeChange,
}: {
  content: string;
  loading: boolean;
  inputMode: InputMode;
  onChange: (value: string) => void;
  onSubmit: (override?: string) => void;
  onInputModeChange: (value: InputMode) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Chế độ Voice: dừng mic -> tự gửi luôn transcript cuối.
  const { recording, supported, start, stop } = useSpeechInput(
    onChange,
    inputMode === "voice" ? (finalText) => onSubmit(finalText) : undefined,
  );
  const isVoice = inputMode === "voice";

  // Auto-resize textarea theo nội dung
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [content]);

  function handleMicClick() {
    if (recording) stop();
    else start(content);
  }

  return (
    <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface)]/95 p-3 shadow-sm backdrop-blur-sm">
      {/* Thanh chế độ: Text / Voice */}
      <div className="mb-2 flex items-center gap-3 px-1">
        <div className="inline-flex rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-1">
          {INPUT_MODES.map((mode) => {
            const active = inputMode === mode.id;
            const Icon = mode.icon;
            return (
              <button
                key={mode.id}
                type="button"
                disabled={loading || recording}
                title={mode.hint}
                onClick={() => onInputModeChange(mode.id)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${
                  active
                    ? "bg-[color:var(--accent)] text-white shadow-sm"
                    : "text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {mode.label}
              </button>
            );
          })}
        </div>
        <p className="hidden text-xs text-[color:var(--text-soft)] sm:block">
          {isVoice ? "Nhấn mic để nói, nhấn lần nữa để gửi — Studify sẽ trả lời bằng giọng nói." : "Gõ và đọc câu trả lời."}
        </p>
      </div>

      {/* Ô nhập + nút */}
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (!isVoice && e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          rows={1}
          readOnly={recording || isVoice}
          className={`min-h-[44px] max-h-[200px] flex-1 resize-none rounded-lg bg-transparent px-3 py-2.5 text-sm leading-6 outline-none transition-all ${
            recording ? "ring-2 ring-rose-400/50" : ""
          }`}
          placeholder={
            recording ? "Đang nghe... nói đi bạn ơi" : isVoice ? "Nhấn mic để nói với Studify..." : "Hỏi Studify..."
          }
        />

        {isVoice ? (
          /* Chế độ Voice: chỉ có nút mic (dừng = gửi luôn) */
          supported ? (
            <button
              type="button"
              onClick={handleMicClick}
              disabled={loading}
              title={recording ? "Dừng & gửi" : "Nhấn để nói"}
              className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm transition disabled:opacity-60 ${
                recording
                  ? "animate-pulse bg-rose-500 text-white"
                  : "bg-[color:var(--accent)] text-white hover:bg-[color:var(--accent-strong)]"
              }`}
            >
              {recording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </button>
          ) : (
            <span className="px-2 text-xs text-[color:var(--text-soft)]">Trình duyệt chưa hỗ trợ nhập giọng nói</span>
          )
        ) : (
          /* Chế độ Text: nút gửi */
          <button
            type="button"
            onClick={() => onSubmit()}
            disabled={loading}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[color:var(--chat-user-bg-strong)] text-[color:var(--chat-user-text)] transition hover:brightness-105 disabled:opacity-60"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Chỉ báo đang ghi âm */}
      {recording ? (
        <div className="mt-2 flex items-center gap-2 px-1">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
          <p className="text-xs text-rose-500">Đang nghe... nhấn mic để dừng và gửi.</p>
        </div>
      ) : null}
    </div>
  );
}

// ── Chat Page ─────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [hasInitializedSelection, setHasInitializedSelection] = useState(false);
  const [content, setContent] = useState("");
  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [streamingReply, setStreamingReply] = useState<StreamingReply | null>(null);
  const [assistantStatus, setAssistantStatus] = useState("Studify đang nghĩ...");
  const [pendingUserMessage, setPendingUserMessage] = useState<{
    sessionId: number | null;
    content: string;
    createdAt: string;
  } | null>(null);
  const [showSafetyBanner, setShowSafetyBanner] = useState(false);
  /** Citations được lưu per-session sau mỗi reply */
  const [sessionCitations, setSessionCitations] = useState<Map<number, CitationItem[]>>(new Map());
  /** Feedback thumbs per message ID */
  const [messageFeedbacks, setMessageFeedbacks] = useState<Map<number, "up" | "down">>(new Map());
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Tải sessions lần đầu
  useEffect(() => {
    getChatSessions().then((data) => {
      const next = sortSessions(data as SessionItem[]);
      setSessions(next);
      if (!hasInitializedSelection && next.length > 0) {
        setSelectedSessionId(next[0].id);
        setHasInitializedSelection(true);
      }
    });
  }, [hasInitializedSelection]);

  // Scroll to bottom khi session thay đổi / tin nhắn mới / switch session
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [sessions, streamingReply, pendingUserMessage, selectedSessionId]);

  // ── Computed ──────────────────────────────────────────────────────────────
  const activeSession =
    selectedSessionId === null
      ? null
      : (sessions.find((s) => s.id === selectedSessionId) ?? null);
  const orderedMessages = activeSession ? sortMessages(activeSession.messages) : [];
  const activeSessionId = activeSession?.id ?? selectedSessionId;
  const hasConversation = Boolean(
    orderedMessages.length || pendingUserMessage || streamingReply,
  );
  const showPendingUser =
    pendingUserMessage &&
    (pendingUserMessage.sessionId === null || pendingUserMessage.sessionId === activeSessionId);

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function refreshSessions(targetSessionId?: number) {
    const updated = sortSessions((await getChatSessions()) as SessionItem[]);
    setSessions(updated);
    if (targetSessionId) {
      setSelectedSessionId(targetSessionId);
      return;
    }
    if (!hasInitializedSelection && !selectedSessionId && updated.length > 0) {
      setSelectedSessionId(updated[0].id);
      setHasInitializedSelection(true);
    }
  }

  async function handleSend(override?: string) {
    // override: transcript cuối từ chế độ Voice (tránh đụng độ state với setContent).
    const prompt = (override ?? content).trim();
    if (!prompt || loading) return;

    // Dừng mọi câu đang được đọc (TTS) khi bắt đầu lượt mới.
    stopSpeaking();

    // Kiểm tra nguy cơ TRƯỚC khi gửi
    if (detectCrisis(prompt)) setShowSafetyBanner(true);

    const targetSessionId = activeSessionId ?? null;

    // Xoá citations cũ khi gửi tin mới
    if (targetSessionId) {
      setSessionCitations((prev) => {
        const next = new Map(prev);
        next.delete(targetSessionId);
        return next;
      });
    }

    setLoading(true);
    setError("");
    setContent("");
    setStreamingReply(null);
    setAssistantStatus("Studify đang nghĩ...");
    setPendingUserMessage({
      sessionId: targetSessionId,
      content: prompt,
      createdAt: new Date().toISOString(),
    });

    try {
      const result = await streamChatMessage(
        { session_id: targetSessionId, content: prompt, chat_mode: "quick" },
        {
          onMeta: (meta) => {
            setSelectedSessionId(meta.session_id);
            setSessions((current) => {
              if (current.some((s) => s.id === meta.session_id)) return current;
              const now = new Date().toISOString();
              return sortSessions([
                {
                  id: meta.session_id,
                  title: generateTitle(prompt),
                  mode: "STUDIFY_QUICK",
                  created_at: now,
                  updated_at: now,
                  messages: [],
                },
                ...current,
              ]);
            });
            setPendingUserMessage((cur) => (cur ? { ...cur, sessionId: meta.session_id } : cur));
            setStreamingReply({ ...meta, answer: "" });
          },
          onStatus: (label) => setAssistantStatus(label),
          onChunk: (delta) => {
            setStreamingReply((cur) => (cur ? { ...cur, answer: cur.answer + delta } : cur));
          },
        },
      );

      // Lưu citations cho session này
      setSessionCitations((prev) => {
        const next = new Map(prev);
        next.set(result.session_id, result.citations ?? []);
        return next;
      });

      // Kích hoạt safety banner nếu backend đánh dấu urgent
      if (result.is_urgent) setShowSafetyBanner(true);

      // Chế độ Voice: Studify đọc câu trả lời bằng giọng nói.
      if (inputMode === "voice" && result.answer) speakText(result.answer);

      setStreamingReply(null);
      await refreshSessions(result.session_id);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Không gửi được tin nhắn.");
      setContent(prompt);
    } finally {
      setPendingUserMessage(null);
      setAssistantStatus("Studify đang nghĩ...");
      setLoading(false);
    }
  }

  async function handleDeleteSession(sessionId: number) {
    await deleteChatSession(sessionId);
    setSessions((current) => {
      const next = current.filter((s) => s.id !== sessionId);
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(next[0]?.id ?? null);
        setStreamingReply(null);
        setPendingUserMessage(null);
        setError("");
        setShowSafetyBanner(false);
      }
      return next;
    });
  }

  async function handleFeedback(messageId: number, sessionId: number, rating: "up" | "down") {
    setMessageFeedbacks((prev) => new Map(prev).set(messageId, rating));
    await sendFeedback({ message_id: messageId, session_id: sessionId, rating }).catch(() => null);
  }

  function handleNewConversation() {
    setSelectedSessionId(null);
    setHasInitializedSelection(true);
    setStreamingReply(null);
    setAssistantStatus("Studify đang nghĩ...");
    setPendingUserMessage(null);
    setContent("");
    setError("");
    setShowSafetyBanner(false);
  }

  // ── Sidebar ───────────────────────────────────────────────────────────────

  const sessionGroups = groupSessions(sessions);

  const sidebarExtra = (
    <div className="space-y-3">
      <button
        type="button"
        onClick={handleNewConversation}
        className="btn-secondary inline-flex w-full items-center justify-start gap-2 rounded-md px-4 py-3 text-sm font-medium transition"
      >
        <Plus className="h-4 w-4" />
        Cuộc trò chuyện mới
      </button>

      {sessions.length === 0 ? (
        <div className="rounded-md border border-dashed border-[color:var(--line)] px-4 py-3 text-sm text-[color:var(--text-muted)]">
          Chưa có lịch sử chat.
        </div>
      ) : (
        <div className="space-y-4">
          {sessionGroups.map((group) => (
            <div key={group.label}>
              <p className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[color:var(--text-soft)]">
                {group.label}
              </p>
              <div className="space-y-1.5">
                {group.items.map((session) => (
                  <div
                    key={session.id}
                    className={`flex items-start gap-1.5 rounded-md border px-3 py-2.5 transition ${
                      activeSession?.id === session.id
                        ? "border-transparent bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                        : "border-[color:var(--line)] bg-[color:var(--surface)] hover:bg-[color:var(--surface-soft)]"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedSessionId(session.id)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="line-clamp-2 text-xs font-medium leading-5">
                        {session.title}
                      </p>
                      <p className="mt-0.5 text-[10px] text-[color:var(--text-muted)]">
                        {formatDateTime(session.updated_at)}
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteSession(session.id)}
                      aria-label={`Xóa ${session.title}`}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full text-[color:var(--text-muted)] transition hover:bg-[color:var(--surface)] hover:text-rose-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <AppShell pageTitle="Chat" hideHeader sidebarExtra={sidebarExtra} variant="assistant">
      <div className="flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 pb-32 pt-8 sm:px-6">
            {!hasConversation ? (
              /* ── Welcome / Empty state ── */
              <div className="flex flex-1 flex-col items-center justify-center">
                <div className="w-full max-w-3xl text-center">
                  <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Studify</h1>
                  <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[color:var(--text-muted)]">
                    Hôm nay bạn cần mình giúp gì? Hỏi về học vụ, lịch, deadline hoặc điều đang làm
                    bạn nặng đầu.
                  </p>
                  <div className="mt-8">
                    <ChatComposer
                      content={content}
                      loading={loading}
                      inputMode={inputMode}
                      onChange={setContent}
                      onSubmit={(override) => void handleSend(override)}
                      onInputModeChange={setInputMode}
                    />
                  </div>
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    {starterPrompts.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setContent(item)}
                        className="rounded-full border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-1.5 text-sm text-[color:var(--text-muted)] transition hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent)]"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                  {error ? (
                    <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
                      {error}
                    </p>
                  ) : null}
                </div>
              </div>
            ) : (
              /* ── Conversation ── */
              <div className="space-y-8">
                {/* Safety banner — hiện khi phát hiện tín hiệu nguy cơ */}
                {showSafetyBanner ? (
                  <WellbeingSafetyBanner onDismiss={() => setShowSafetyBanner(false)} />
                ) : null}

                {orderedMessages.map((message, index) => {
                  const isAssistant = message.role === "assistant";
                  const isLastMsg = index === orderedMessages.length - 1;
                  // Citations: chỉ hiển thị cho tin nhắn AI cuối cùng trong session
                  const citations =
                    isAssistant && isLastMsg && activeSessionId != null
                      ? (sessionCitations.get(activeSessionId) ?? [])
                      : [];
                  return (
                    <div key={message.id} className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
                      <div className={`${isAssistant ? "w-full max-w-3xl" : "max-w-2xl"}`}>
                        {/* Header tin nhắn */}
                        <div className="mb-2 flex items-center gap-2 text-xs">
                          {isAssistant ? (
                            <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-[color:var(--accent)] text-white">
                              <MessageCircleHeart className="h-3.5 w-3.5" />
                            </span>
                          ) : null}
                          <span
                            className={
                              isAssistant
                                ? "font-semibold text-[color:var(--text-primary)]"
                                : "font-semibold text-[color:var(--text-muted)]"
                            }
                          >
                            {isAssistant ? "Studify" : "Bạn"}
                          </span>
                          <span className="text-[color:var(--text-soft)]">
                            {formatDateTime(message.created_at)}
                          </span>
                          {/* Badge category — chỉ dùng category của chính tin nhắn đó */}
                          {isAssistant && message.category ? (
                            <span className="rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[10px] text-[color:var(--accent)]">
                              {message.category}
                            </span>
                          ) : null}
                        </div>

                        {/* Nội dung */}
                        {isAssistant ? (
                          <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-4">
                            <MarkdownContent content={message.content} className="text-sm" />

                            {/* Citation cards */}
                            <CitationCards citations={citations} />

                            {/* Toolbar: copy + feedback */}
                            <div className="mt-3 flex items-center gap-1 border-t border-[color:var(--line)] pt-3">
                              <CopyButton text={message.content} />
                              <MessageFeedback
                                messageId={message.id}
                                sessionId={activeSessionId ?? 0}
                                voted={messageFeedbacks.get(message.id) ?? null}
                                onVote={handleFeedback}
                              />
                            </div>
                          </div>
                        ) : (
                          <div className="inline-flex rounded-xl bg-[color:var(--chat-user-bg)] px-5 py-4 text-[color:var(--chat-user-text)] shadow-sm">
                            <p className="whitespace-pre-wrap text-sm leading-7">
                              {message.content}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Tin nhắn người dùng đang chờ (optimistic) */}
                {showPendingUser ? (
                  <div className="flex justify-end">
                    <div className="max-w-2xl rounded-xl bg-[color:var(--chat-user-bg)] px-5 py-4 text-[color:var(--chat-user-text)] shadow-sm">
                      <div className="mb-2 text-xs text-[color:var(--chat-user-text)]/70">
                        {formatDateTime(pendingUserMessage.createdAt)}
                      </div>
                      <p className="whitespace-pre-wrap text-sm leading-7">
                        {pendingUserMessage.content}
                      </p>
                    </div>
                  </div>
                ) : null}

                {/* Thinking dots */}
                {loading && (!streamingReply || !streamingReply.answer.trim()) ? (
                  <div className="flex justify-start">
                    <div className="w-full max-w-3xl">
                      <AssistantStatusHeader status={assistantStatus} />
                      <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-4">
                        <div className="thinking-dots">
                          <span />
                          <span />
                          <span />
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {/* Streaming answer */}
                {streamingReply?.answer.trim() ? (
                  <div className="flex justify-start">
                    <div className="w-full max-w-3xl">
                      <AssistantStatusHeader
                        status={assistantStatus || "Studify đang trả lời..."}
                      />
                      <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-4">
                        <MarkdownContent content={streamingReply.answer} className="text-sm" />
                        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle opacity-60" />
                        {/* Citations trong lúc streaming */}
                        {(streamingReply.citations?.length ?? 0) > 0 ? (
                          <CitationCards citations={streamingReply.citations} />
                        ) : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {/* Composer dính đáy khi đang hội thoại */}
        {hasConversation ? (
          <div className="border-t border-[color:var(--line)] bg-[color:var(--page-bg)] px-4 py-4 sm:px-6">
            <div className="mx-auto w-full max-w-4xl">
              {error ? (
                <p className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
                  {error}
                </p>
              ) : null}
              <ChatComposer
                content={content}
                loading={loading}
                inputMode={inputMode}
                onChange={setContent}
                onSubmit={(override) => void handleSend(override)}
                onInputModeChange={setInputMode}
              />
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
