import { readAuth, type StoredUser } from "@/lib/auth";

const API_BASE = "/api/v1";

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
  advisor_summary: Record<string, number | string | null>;
};

export type AdminRuntime = {
  queue_size: number;
  refresh_schedule: Record<string, unknown>;
  refresh_runtime: Record<string, unknown>;
};

export type AdminDocument = {
  id: number;
  title: string;
  url: string;
  group_name?: string | null;
  file_type?: string | null;
  is_official_uit: boolean;
  updated_source_at?: string | null;
  vector_metadata?: Record<string, unknown> | null;
};

export type AdminUploadResult = {
  document_id: number;
  title: string;
  status: string;
  chunk_count: number;
  used_ocr: boolean;
  group_name: string;
  file_type: string;
  is_official_uit: boolean;
  url: string;
};

export type AdvisorIdentity = {
  student_name: string;
  student_id: string;
  faculty: string;
  major: string;
  class_name: string;
  cohort_label: string;
  birth_year_hint?: number | null;
  expected_graduation_term?: string | null;
};

export type AdvisorCourseStatus = {
  course_id: number;
  code: string;
  name: string;
  credits: number;
  category: string;
  recommended_semester: number;
  requirement_group: string;
  status: string;
  status_label: string;
  letter_grade?: string | null;
  semester_code?: string | null;
  prerequisites: string[];
};

export type DegreeAudit = {
  identity: AdvisorIdentity;
  program_name: string;
  total_required_credits: number;
  passed_credits: number;
  in_progress_credits: number;
  remaining_credits: number;
  completion_percent: number;
  english_requirement?: string | null;
  milestone_summary: string;
  category_progress: Array<{ category: string; required_credits: number; passed_credits: number; remaining_credits: number }>;
  required_courses: AdvisorCourseStatus[];
  missing_core_courses: string[];
};

export type SemesterPlanning = {
  identity: AdvisorIdentity;
  recommended_credit_load: number;
  blocking_courses: string[];
  semesters: Array<{
    title: string;
    semester_code: string;
    total_credits: number;
    max_credits: number;
    notes: string;
    courses: Array<{
      course_id: number;
      code: string;
      name: string;
      credits: number;
      category: string;
      planned_reason: string;
      prerequisite_codes: string[];
    }>;
  }>;
  graph_nodes: Array<{
    course_id: number;
    code: string;
    name: string;
    credits: number;
    recommended_semester: number;
    category: string;
    status: string;
    plan_slot?: number | null;
  }>;
  graph_edges: Array<{
    from_course_id: number;
    to_course_id: number;
    prerequisite_type: string;
  }>;
};

export type AcademicRiskAlert = {
  identity: AdvisorIdentity;
  risk_level: string;
  risk_score: number;
  summary: string;
  signals: string[];
  recommendations: string[];
  overdue_task_count: number;
  failed_course_count: number;
  current_gpa?: number | null;
  cumulative_gpa?: number | null;
};

export type AdvisorOverview = {
  degree_audit: DegreeAudit;
  semester_planning: SemesterPlanning;
  academic_risk: AcademicRiskAlert;
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

export type Profile = {
  user_id: number;
  username: string;
  full_name: string;
  email?: string | null;
  role: string;
  student_id?: string | null;
  faculty?: string | null;
  major?: string | null;
  class_name?: string | null;
  cohort?: string | null;
  advisor_name?: string | null;
};

export type Course = {
  id: number;
  code: string;
  name: string;
  credits: number;
  category: string;
  department_name?: string | null;
  description?: string | null;
  requirement_groups: string[];
  recommended_semesters: number[];
  prerequisite_codes: string[];
};

export type GpaCourseInput = {
  course_code?: string | null;
  name?: string | null;
  credits: number;
  grade?: string | null;
  numeric_grade?: number | null;
};

export type WellbeingNote = {
  id: number;
  title: string;
  content: string;
  mood_code?: string | null;
  is_private: boolean;
  needs_human_support: boolean;
  created_at: string;
  updated_at: string;
};

export type WellbeingCheckin = {
  id: number;
  mood_code: string;
  valence: number;
  energy: number;
  stress: number;
  motivation: number;
  focus: number;
  sleep_quality?: number | null;
  note_preview?: string | null;
  needs_human_support: boolean;
  created_at: string;
};

export type SpotifyStatus = {
  enabled: boolean;
  connected: boolean;
  spotify_user_id?: string | null;
  display_name?: string | null;
  scopes: string[];
  uses_curated_fallback: boolean;
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

async function requestForm<T>(path: string, body: FormData): Promise<T> {
  const headers = new Headers();
  Object.entries(authHeaders()).forEach(([key, value]) => {
    if (value) {
      headers.set(key, value);
    }
  });

  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as T;
}

async function parseError(response: Response) {
  const error = await response.json().catch(() => ({ detail: "Đã có lỗi xảy ra." }));
  const detail = error.detail;
  if (!detail) return "Đã có lỗi xảy ra.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg ?? "Lỗi không xác định").join("; ");
  }
  return "Đã có lỗi xảy ra.";
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
  return request<DashboardOverview>("/dashboard/overview");
}

export async function getProfile() {
  return request<Profile>("/profile");
}

export async function updateProfile(payload: Partial<Profile>) {
  return request<Profile>("/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getAdvisorOverview() {
  return request<AdvisorOverview>("/advisor/overview");
}

export async function getAdvisorAudit() {
  return request<DegreeAudit>("/advisor/audit");
}

export async function getAdvisorPlan() {
  return request<SemesterPlanning>("/advisor/plan");
}

export async function getAdvisorRisk() {
  return request<AcademicRiskAlert>("/advisor/risk");
}

export async function getCourses(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<Course[]>(`/courses${query}`, undefined, []);
}

export async function getGpaHistory() {
  return request<Array<Record<string, unknown>>>("/gpa/history", undefined, []);
}

export async function calculateGpa(courses: GpaCourseInput[]) {
  return request<Record<string, unknown>>("/gpa/calculate", {
    method: "POST",
    body: JSON.stringify({ courses }),
  });
}

export async function simulateGpa(plannedCourses: GpaCourseInput[]) {
  return request<Record<string, unknown>>("/gpa/simulate", {
    method: "POST",
    body: JSON.stringify({ planned_courses: plannedCourses }),
  });
}

export async function analyzeAcademicRisk() {
  return request<AcademicRiskAlert>("/academic-risk/analyze", {
    method: "POST",
    body: JSON.stringify({ include_recommendations: true }),
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

export async function getDocuments(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<Array<Record<string, unknown>>>(`/documents${query}`, undefined, []);
}

export async function searchStudify(q: string) {
  return request<Record<string, Array<Record<string, unknown>> | string>>(`/search?q=${encodeURIComponent(q)}`);
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
  return request<EnergyInsight>("/diary/insight");
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

export async function getWellbeingCheckins() {
  return request<WellbeingCheckin[]>("/wellbeing/checkins", undefined, []);
}

export async function createWellbeingCheckin(payload: Record<string, unknown>) {
  return request<WellbeingCheckin>("/wellbeing/checkins", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getWellbeingNotes() {
  return request<WellbeingNote[]>("/wellbeing/notes", undefined, []);
}

export async function createWellbeingNote(payload: Record<string, unknown>) {
  return request<WellbeingNote>("/wellbeing/notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteWellbeingNote(noteId: number) {
  return request<{ deleted: boolean }>(`/wellbeing/notes/${noteId}`, { method: "DELETE" });
}

export async function getWellbeingMusic(theme = "focus") {
  return request<MusicTrack[]>(`/wellbeing/music?theme=${encodeURIComponent(theme)}`, undefined, []);
}

export async function getSpotifyStatus() {
  return request<SpotifyStatus>("/integrations/spotify/status");
}

export async function connectSpotifyPreview(payload: Record<string, unknown>) {
  return request<SpotifyStatus>("/integrations/spotify/connect-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function disconnectSpotify() {
  return request<SpotifyStatus>("/integrations/spotify/disconnect", { method: "POST" });
}

export type SpotifyPlaylistItem = {
  id: string;
  name: string;
  description?: string | null;
  image_url?: string | null;
  tracks_total: number;
  external_url?: string | null;
  embed_url?: string | null;
};

export async function getSpotifyPlaylists() {
  return request<SpotifyPlaylistItem[]>("/integrations/spotify/playlists", undefined, []);
}

export async function createSpotifyPlaylistMapping(payload: { spotify_playlist_id: string; theme: string }) {
  return request<{ id: number; spotify_playlist_id: string; theme: string; title: string }>(
    "/integrations/spotify/playlist-mappings",
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function spotifyConnectUrl(apiBase: string) {
  return `${apiBase}/integrations/spotify/connect`;
}

export async function sendFeedback(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>("/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAdminOverview() {
  return request<Record<string, number | string>>("/admin/overview");
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

export async function getAdminRuntime() {
  return request<AdminRuntime>("/admin/runtime");
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

export async function getAdminManualDocuments() {
  return request<AdminDocument[]>("/admin/manual-documents", undefined, []);
}

export async function uploadAdminDocument(payload: FormData) {
  return requestForm<AdminUploadResult>("/admin/uploads", payload);
}

// ── Study Plan ───────────────────────────────────────────────────────────────

export type StudyPlanCourse = {
  id: number;
  course_code: string;
  course_name: string;
  credits: number;
  category?: string | null;
  is_required: boolean;
  note?: string | null;
};

export type StudyPlanSemester = {
  id: number;
  label: string;
  sort_order: number;
  max_credits: number;
  total_credits: number;
  notes?: string | null;
  courses: StudyPlanCourse[];
};

export type StudyPlan = {
  id: number;
  name: string;
  description?: string | null;
  target_graduation_year?: number | null;
  total_required_credits: number;
  max_credits_per_semester: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  semesters: StudyPlanSemester[];
};

export type ValidationIssue = {
  severity: "error" | "warning";
  code: string;
  message: string;
  course_code?: string | null;
  semester_label?: string | null;
};

export type StudyPlanValidationResult = {
  valid: boolean;
  issues: ValidationIssue[];
  total_planned_credits: number;
  accumulated_unique_credits: number;
  graduation_progress_pct: number;
};

export async function getStudyPlans() {
  return request<StudyPlan[]>("/study-plans", undefined, []);
}

export async function createStudyPlan(payload: Partial<StudyPlan>) {
  return request<StudyPlan>("/study-plans", { method: "POST", body: JSON.stringify(payload) });
}

export async function getStudyPlan(planId: number) {
  return request<StudyPlan>(`/study-plans/${planId}`);
}

export async function updateStudyPlan(planId: number, payload: Partial<StudyPlan>) {
  return request<StudyPlan>(`/study-plans/${planId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteStudyPlan(planId: number) {
  return request<{ deleted: boolean }>(`/study-plans/${planId}`, { method: "DELETE" });
}

export async function addSemester(planId: number, payload: { label: string; max_credits?: number; sort_order?: number }) {
  return request<StudyPlanSemester>(`/study-plans/${planId}/semesters`, { method: "POST", body: JSON.stringify(payload) });
}

export async function removeSemester(planId: number, semesterId: number) {
  return request<{ deleted: boolean }>(`/study-plans/${planId}/semesters/${semesterId}`, { method: "DELETE" });
}

export async function addCourseToSemester(planId: number, semesterId: number, payload: { course_code: string; course_name: string; credits: number; category?: string }) {
  return request<StudyPlanCourse>(`/study-plans/${planId}/semesters/${semesterId}/courses`, { method: "POST", body: JSON.stringify(payload) });
}

export async function removeCourseFromSemester(planId: number, semesterId: number, courseCode: string) {
  return request<{ deleted: boolean }>(`/study-plans/${planId}/semesters/${semesterId}/courses/${encodeURIComponent(courseCode)}`, { method: "DELETE" });
}

export async function validateStudyPlan(planId: number) {
  return request<StudyPlanValidationResult>(`/study-plans/${planId}/validate`, { method: "POST" });
}

// ── Notifications ────────────────────────────────────────────────────────────

export type AppNotification = {
  id: number;
  title: string;
  content: string;
  is_read: boolean;
  action_link?: string | null;
  created_at: string;
};

export async function getNotifications() {
  return request<AppNotification[]>("/notifications", undefined, []);
}

export async function markNotificationRead(notificationId: number) {
  return request<{ updated: boolean }>(`/notifications/${notificationId}/read`, { method: "POST" });
}

// ── Wellbeing dashboard ──────────────────────────────────────────────────────

export async function getWellbeingDashboard() {
  return request<Record<string, unknown>>("/wellbeing/dashboard", undefined, {});
}

export async function deleteWellbeingCheckin(checkinId: number) {
  return request<{ deleted: boolean }>(`/wellbeing/checkins/${checkinId}`, { method: "DELETE" });
}

export async function deleteAllWellbeingCheckins() {
  return request<{ deleted: number }>("/wellbeing/checkins", { method: "DELETE" });
}

export async function aiReflectNote(noteId: number) {
  return request<{ reflection: string; suggestions: string[] }>(`/wellbeing/notes/${noteId}/ai-reflect`, { method: "POST" });
}

// ── Admin music playlists ────────────────────────────────────────────────────

export type MusicPlaylist = {
  id: number;
  theme: string;
  title: string;
  description?: string | null;
  spotify_url?: string | null;
  embed_url?: string | null;
  cover_url?: string | null;
  is_active: boolean;
};

export async function getAdminMusicPlaylists(theme?: string) {
  const q = theme ? `?theme=${encodeURIComponent(theme)}` : "";
  return request<MusicPlaylist[]>(`/wellbeing/music/playlists${q}`, undefined, []);
}

export async function createMusicPlaylist(payload: Partial<MusicPlaylist>) {
  return request<MusicPlaylist>("/wellbeing/music/playlists", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateMusicPlaylist(playlistId: number, payload: Partial<MusicPlaylist>) {
  return request<MusicPlaylist>(`/wellbeing/music/playlists/${playlistId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteMusicPlaylist(playlistId: number) {
  return request<{ deleted: boolean }>(`/wellbeing/music/playlists/${playlistId}`, { method: "DELETE" });
}
