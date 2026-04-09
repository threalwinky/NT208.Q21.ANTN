import { readAuth, type StoredUser } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type LoginResponse = {
  access_token: string;
  token_type: string;
  user: StoredUser;
};

type DashboardOverview = {
  announcements: Array<{ id: number; title: string; group_name: string; published_at?: string | null; url: string }>;
  upcoming_tasks: Array<{ id: number; title: string; task_type: string; due_at?: string | null; status: string; priority: string }>;
  today_schedule: Array<{ title: string; item_type: string; starts_at: string; ends_at?: string | null; location?: string | null }>;
  mood_label?: string | null;
  latest_energy_level: number;
  latest_energy_label: string;
  energy_summary: string;
  energy_trend: string;
  metrics: Record<string, number>;
};

export type CitationItem = {
  document_id: number;
  title: string;
  url: string;
  source_label: string;
  confidence: string;
  excerpt: string;
  updated_at?: string | null;
};

export type ChatReply = {
  session_id: number;
  category: string;
  answer: string;
  is_urgent: boolean;
  risk_score: number;
  citations: CitationItem[];
  action_suggestions: string[];
};

export type JournalRecommendation = {
  kind: string;
  title: string;
  subtitle: string;
  description: string;
  url?: string | null;
  image_url?: string | null;
};

export type MusicTrack = {
  title: string;
  artist: string;
  album: string;
  url: string;
  embed_url: string;
  image_url?: string | null;
};

export type EnergyInsight = {
  latest_energy_level: number;
  latest_energy_label: string;
  latest_mood_label?: string | null;
  average_energy_level: number;
  trend: string;
  summary: string;
  signals: string[];
  low_energy_threshold: number;
  recommendation_mode: string;
  recommendations: JournalRecommendation[];
  music_theme: string;
  music_theme_label: string;
  music_tracks: MusicTrack[];
  energy_series: number[];
};

export type MoodJournal = {
  id: number;
  short_note?: string | null;
  energy_level: number;
  energy_label: string;
  energy_summary: string;
  signals: string[];
  needs_human_support: boolean;
  created_at: string;
  mood_label?: string | null;
};

type ChatStreamMeta = {
  type: "meta";
  session_id: number;
  category: string;
  is_urgent: boolean;
  risk_score: number;
  citations: CitationItem[];
  action_suggestions: string[];
};

type ChatStreamChunk = {
  type: "chunk";
  delta: string;
};

type ChatStreamStatus = {
  type: "status";
  label: string;
};

type ChatStreamDone = ChatReply & {
  type: "done";
};

type ChatStreamError = {
  type: "error";
  message: string;
};

type ChatStreamEvent = ChatStreamMeta | ChatStreamChunk | ChatStreamStatus | ChatStreamDone | ChatStreamError;

function authHeaders() {
  const auth = readAuth();
  return auth?.token ? { Authorization: `Bearer ${auth.token}` } : {};
}

async function request<T>(path: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const headers = new Headers(init?.headers);
    headers.set("Content-Type", "application/json");
    Object.entries(authHeaders()).forEach(([key, value]) => {
      if (value) {
        headers.set(key, value);
      }
    });

    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Đã có lỗi xảy ra." }));
      throw new Error(error.detail ?? "Đã có lỗi xảy ra.");
    }

    return (await response.json()) as T;
  } catch (error) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

async function parseError(response: Response) {
  const error = await response.json().catch(() => ({ detail: "Đã có lỗi xảy ra." }));
  return error.detail ?? "Đã có lỗi xảy ra.";
}

export async function login(username: string, password: string) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getMe() {
  return request<StoredUser>("/auth/me");
}

export async function getDashboardOverview() {
  return request<DashboardOverview>("/dashboard/overview", undefined, {
    announcements: [
      {
        id: 1,
        title: "Thông báo mở đăng ký học phần học kỳ hè 2025-2026",
        group_name: "Học vụ",
        published_at: new Date().toISOString(),
        url: "https://student.uit.edu.vn",
      },
      {
        id: 2,
        title: "CTSV phát động tuần lễ kỹ năng và hỗ trợ tâm lý đầu học kỳ",
        group_name: "Tâm lý",
        published_at: new Date(Date.now() - 86400000).toISOString(),
        url: "https://ctsv.uit.edu.vn",
      },
    ],
    upcoming_tasks: [
      {
        id: 1,
        title: "Hoàn tất báo cáo đồ án tuần 6",
        task_type: "Đồ án",
        due_at: new Date(Date.now() + 3 * 86400000).toISOString(),
        status: "TODO",
        priority: "HIGH",
      },
    ],
    today_schedule: [
      {
        title: "Trí tuệ nhân tạo",
        item_type: "LỊCH HỌC",
        starts_at: new Date(Date.now() + 2 * 3600000).toISOString(),
        ends_at: new Date(Date.now() + 5 * 3600000).toISOString(),
        location: "A306",
      },
    ],
    mood_label: "Hơi mệt",
    latest_energy_level: 3,
    latest_energy_label: "Trung bình",
    energy_summary: "Năng lượng đang ở mức vừa. Nên giữ một việc chính, phần còn lại chia nhỏ để đỡ ngợp.",
    energy_trend: "STABLE",
    metrics: {
      totalAnnouncements: 24,
      openTasks: 5,
      upcomingExams: 2,
      moodCheckins: 7,
    },
  });
}

export async function getAnnouncements(groupName?: string) {
  const query = groupName ? `?group_name=${encodeURIComponent(groupName)}` : "";
  return request<Array<Record<string, unknown>>>(`/announcements${query}`, undefined, []);
}

export async function toggleSaveAnnouncement(announcementId: number) {
  return request<{ isSaved: boolean }>(`/announcements/${announcementId}/save`, { method: "POST" });
}

export async function getStudyDocuments() {
  return request<Array<Record<string, unknown>>>("/planner/documents", undefined, []);
}

export async function getAcademicEvents() {
  return request<Array<Record<string, unknown>>>("/planner/events", undefined, []);
}

export async function getClassSchedule() {
  return request<Array<Record<string, unknown>>>("/planner/class-schedule", undefined, []);
}

export async function getExamSchedule() {
  return request<Array<Record<string, unknown>>>("/planner/exam-schedule", undefined, []);
}

export async function getTasks() {
  return request<Array<Record<string, unknown>>>("/planner/tasks", undefined, []);
}

export async function createTask(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>("/planner/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function completeTask(taskId: number) {
  return request<Record<string, unknown>>(`/planner/tasks/${taskId}/complete`, { method: "PATCH" });
}

export async function getChatSessions() {
  return request<Array<Record<string, unknown>>>("/chat/sessions", undefined, []);
}

export async function deleteChatSession(sessionId: number) {
  return request<{ deleted: boolean }>(`/chat/sessions/${sessionId}`, { method: "DELETE" });
}

export async function sendChatMessage(payload: { session_id?: number | null; content: string }) {
  return request<ChatReply>("/chat/send", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function streamChatMessage(
  payload: { session_id?: number | null; content: string },
  handlers?: {
    onMeta?: (meta: Omit<ChatReply, "answer">) => void | Promise<void>;
    onStatus?: (label: string) => void | Promise<void>;
    onChunk?: (delta: string) => void | Promise<void>;
  },
): Promise<ChatReply> {
  const headers = new Headers({ "Content-Type": "application/json" });
  Object.entries(authHeaders()).forEach(([key, value]) => {
    if (value) {
      headers.set(key, value);
    }
  });

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  if (!response.body) {
    throw new Error("Không nhận được dữ liệu stream từ máy chủ.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalReply: ChatReply | null = null;

  async function processEventBlock(block: string) {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) {
      return;
    }

    const event = JSON.parse(data) as ChatStreamEvent;
    if (event.type === "meta") {
      await handlers?.onMeta?.({
        session_id: event.session_id,
        category: event.category,
        is_urgent: event.is_urgent,
        risk_score: event.risk_score,
        citations: event.citations,
        action_suggestions: event.action_suggestions,
      });
      return;
    }

    if (event.type === "chunk") {
      await handlers?.onChunk?.(event.delta);
      return;
    }

    if (event.type === "status") {
      await handlers?.onStatus?.(event.label);
      return;
    }

    if (event.type === "done") {
      finalReply = {
        session_id: event.session_id,
        category: event.category,
        answer: event.answer,
        is_urgent: event.is_urgent,
        risk_score: event.risk_score,
        citations: event.citations,
        action_suggestions: event.action_suggestions,
      };
      return;
    }

    throw new Error(event.message);
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      await processEventBlock(block);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    await processEventBlock(buffer);
  }

  if (!finalReply) {
    throw new Error("Phiên chat đã kết thúc nhưng không nhận được phản hồi hoàn chỉnh.");
  }

  return finalReply;
}

export async function getMoods() {
  return request<Array<Record<string, unknown>>>("/diary/moods", undefined, []);
}

export async function getMoodJournals() {
  return request<MoodJournal[]>("/diary/journals", undefined, []);
}

export async function createMoodCheckin(payload: Record<string, unknown>) {
  return request<MoodJournal>("/diary/checkin", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getEnergyInsight() {
  return request<EnergyInsight>("/diary/insight", undefined, {
    latest_energy_level: 3,
    latest_energy_label: "Trung bình",
    latest_mood_label: "Hơi mệt",
    average_energy_level: 3,
    trend: "STABLE",
    summary: "Năng lượng đang ở mức vừa. Bạn nên giữ một việc chính và chia nhỏ phần còn lại.",
    signals: ["hơi mệt"],
    low_energy_threshold: 2.4,
    recommendation_mode: "story",
    recommendations: [
      {
        kind: "story",
        title: "Bắt đầu lại từ 10 phút",
        subtitle: "Nhắc nhẹ",
        description: "Có những ngày chỉ cần bắt đầu 10 phút là đủ để kéo mình trở lại nhịp học.",
      },
    ],
    music_theme: "focus",
    music_theme_label: "Tập trung nhẹ",
    music_tracks: [],
    energy_series: [3, 2, 3, 4],
  });
}

export async function previewEnergyInsight(payload: { mood_state_id?: number | null; short_note?: string | null }) {
  return request<EnergyInsight>("/diary/insight-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getSupportResources() {
  return request<Array<Record<string, unknown>>>("/diary/resources", undefined, []);
}

export async function getAdminOverview() {
  return request<Record<string, number>>("/admin/overview", undefined, {
    totalSources: 5,
    totalDocuments: 12,
    totalFaqs: 6,
    recentCrawlerRuns: 8,
  });
}

export async function getAdminSources() {
  return request<Array<Record<string, unknown>>>("/admin/sources", undefined, []);
}

export async function updateAdminSource(sourceId: number, isEnabled: boolean) {
  return request<Record<string, unknown>>(`/admin/sources/${sourceId}`, {
    method: "PATCH",
    body: JSON.stringify({ is_enabled: isEnabled }),
  });
}

export async function runCrawl(sourceId: number) {
  return request<Record<string, unknown>>(`/admin/sources/${sourceId}/crawl`, { method: "POST" });
}

export async function reindexAll() {
  return request<Record<string, unknown>>("/admin/reindex", { method: "POST" });
}

export async function runKnowledgeRefresh() {
  return request<Record<string, unknown>>("/admin/knowledge-refresh", { method: "POST" });
}

export async function getCrawlerLogs() {
  return request<Array<Record<string, unknown>>>("/admin/crawler-logs", undefined, []);
}

export async function getConfigs() {
  return request<Array<Record<string, unknown>>>("/admin/configs", undefined, []);
}

export async function upsertConfig(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>("/admin/configs", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
