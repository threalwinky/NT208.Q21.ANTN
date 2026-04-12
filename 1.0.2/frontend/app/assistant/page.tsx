"use client";

import { MessageCircleHeart, Plus, Send, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { MarkdownContent } from "@/components/markdown-content";
import { deleteChatSession, getChatSessions, streamChatMessage, type ChatReply } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

type SessionItem = {
  id: number;
  title: string;
  mode: string;
  created_at: string;
  updated_at: string;
  messages: Array<{
    id: number;
    role: string;
    category?: string | null;
    content: string;
    created_at: string;
  }>;
};

type StreamingReply = Omit<ChatReply, "answer"> & {
  answer: string;
};

function sortSessions(items: SessionItem[]) {
  return [...items].sort((left, right) => {
    const leftTime = new Date(left.updated_at).getTime();
    const rightTime = new Date(right.updated_at).getTime();
    return rightTime - leftTime;
  });
}

function sortMessages(messages: SessionItem["messages"]) {
  return [...messages].sort((left, right) => {
    const leftTime = new Date(left.created_at).getTime();
    const rightTime = new Date(right.created_at).getTime();
    if (leftTime !== rightTime) {
      return leftTime - rightTime;
    }
    return left.id - right.id;
  });
}

const starterPrompts = [
  "Tuần này có thông báo học vụ gì?",
  "Cách xin giấy xác nhận sinh viên?",
  "Mình hơi áp lực vì deadline dồn.",
  "Giúp mình sắp lại tuần này.",
];

function ChatComposer({
  content,
  loading,
  onChange,
  onSubmit,
}: {
  content: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="rounded-[28px] border border-[color:var(--line)] bg-[color:var(--surface)]/95 p-3 shadow-[0_12px_32px_rgba(15,23,42,0.05)] backdrop-blur-sm">
      <div className="flex items-end gap-3">
        <textarea
          value={content}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
          className="min-h-[60px] flex-1 resize-none rounded-[20px] bg-transparent px-3 py-3 text-sm leading-7 outline-none"
          placeholder="Hỏi Studify..."
        />
        <button
          type="button"
          onClick={onSubmit}
          disabled={loading}
          className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--chat-user-bg-strong)] text-[color:var(--chat-user-text)] text-sm font-semibold transition hover:brightness-105 disabled:opacity-60"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [hasInitializedSelection, setHasInitializedSelection] = useState(false);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reply, setReply] = useState<ChatReply | null>(null);
  const [streamingReply, setStreamingReply] = useState<StreamingReply | null>(null);
  const [assistantStatus, setAssistantStatus] = useState("Studify đang nghĩ...");
  const [pendingUserMessage, setPendingUserMessage] = useState<{
    sessionId: number | null;
    content: string;
    createdAt: string;
  } | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    getChatSessions().then((data) => {
      const nextSessions = sortSessions(data as SessionItem[]);
      setSessions(nextSessions);
      if (!hasInitializedSelection && nextSessions.length > 0) {
        setSelectedSessionId(nextSessions[0].id);
        setHasInitializedSelection(true);
      }
    });
  }, [hasInitializedSelection]);

  useEffect(() => {
    if (!scrollRef.current) {
      return;
    }
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [sessions, streamingReply, pendingUserMessage]);

  const activeSession = selectedSessionId === null ? null : sessions.find((item) => item.id === selectedSessionId) ?? null;
  const orderedMessages = activeSession ? sortMessages(activeSession.messages) : [];
  const activeSessionId = activeSession?.id ?? selectedSessionId;
  const visibleReply =
    (streamingReply && streamingReply.session_id === activeSessionId ? streamingReply : null) ??
    (reply && reply.session_id === activeSessionId ? reply : null);
  const showPendingUser =
    pendingUserMessage &&
    (pendingUserMessage.sessionId === null || pendingUserMessage.sessionId === activeSessionId);
  const hasConversation = Boolean(orderedMessages.length || showPendingUser || streamingReply);

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

  async function handleSend() {
    const prompt = content.trim();
    if (!prompt || loading) {
      return;
    }

    const targetSessionId = activeSessionId ?? null;
    setLoading(true);
    setError("");
    setContent("");
    setReply(null);
    setStreamingReply(null);
    setAssistantStatus("Studify đang nghĩ...");
    setPendingUserMessage({
      sessionId: targetSessionId,
      content: prompt,
      createdAt: new Date().toISOString(),
    });

    try {
      const result = await streamChatMessage(
        {
          session_id: targetSessionId,
          content: prompt,
        },
        {
          onMeta: (meta) => {
            setSelectedSessionId(meta.session_id);
            setSessions((current) => {
              if (current.some((item) => item.id === meta.session_id)) {
                return current;
              }
              const createdAt = new Date().toISOString();
              return sortSessions([
                {
                  id: meta.session_id,
                  title: prompt.slice(0, 80),
                  mode: "STUDIFY",
                  created_at: createdAt,
                  updated_at: createdAt,
                  messages: [],
                },
                ...current,
              ]);
            });
            setPendingUserMessage((current) => (current ? { ...current, sessionId: meta.session_id } : current));
            setStreamingReply({ ...meta, answer: "" });
          },
          onStatus: (label) => {
            setAssistantStatus(label);
          },
          onChunk: (delta) => {
            setStreamingReply((current) => (current ? { ...current, answer: `${current.answer}${delta}` } : current));
          },
        },
      );

      setReply(result);
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
      const nextSessions = current.filter((item) => item.id !== sessionId);
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(nextSessions[0]?.id ?? null);
        setReply(null);
        setStreamingReply(null);
        setPendingUserMessage(null);
        setError("");
      }
      return nextSessions;
    });
  }

  const sidebarExtra = (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => {
          setSelectedSessionId(null);
          setHasInitializedSelection(true);
          setReply(null);
          setStreamingReply(null);
          setAssistantStatus("Studify đang nghĩ...");
          setPendingUserMessage(null);
          setContent("");
          setError("");
        }}
        className="btn-secondary inline-flex w-full items-center justify-start gap-2 rounded-[18px] px-4 py-3 text-sm font-medium transition"
      >
        <Plus className="h-4 w-4" />
        Cuộc trò chuyện mới
      </button>

      <div className="space-y-2">
        {sessions.length === 0 ? (
          <div className="rounded-[18px] border border-dashed border-[color:var(--line)] px-4 py-3 text-sm text-[color:var(--text-muted)]">
            Chưa có lịch sử chat.
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`flex items-start gap-2 rounded-[18px] border px-3 py-3 transition ${
                activeSession?.id === session.id
                  ? "border-transparent bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                  : "border-[color:var(--line)] bg-[color:var(--surface)] hover:bg-[color:var(--surface-soft)]"
              }`}
            >
              <button type="button" onClick={() => setSelectedSessionId(session.id)} className="min-w-0 flex-1 text-left">
                <p className="line-clamp-2 text-sm font-medium">{session.title}</p>
                <p className="mt-1 text-xs text-[color:var(--text-muted)]">{formatDateTime(session.updated_at)}</p>
              </button>
              <button
                type="button"
                onClick={() => void handleDeleteSession(session.id)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-full text-[color:var(--text-muted)] transition hover:bg-[color:var(--surface)] hover:text-rose-500"
                aria-label={`Xóa cuộc trò chuyện ${session.title}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );

  return (
    <AppShell pageTitle="Chat" hideHeader sidebarExtra={sidebarExtra} variant="assistant">
      <div className="flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 pb-28 pt-8 sm:px-6">
            {!hasConversation ? (
              <div className="flex flex-1 flex-col items-center justify-center">
                <div className="w-full max-w-3xl text-center">
                  <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Studify</h1>
                  <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[color:var(--text-muted)]">
                    Hôm nay bạn cần mình giúp gì? Hỏi về học vụ, lịch, deadline hoặc nói ngắn gọn điều đang làm bạn nặng đầu.
                  </p>
                  <div className="mt-8">
                    <ChatComposer content={content} loading={loading} onChange={setContent} onSubmit={() => void handleSend()} />
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
                    <p className="mt-4 rounded-[16px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
                      {error}
                    </p>
                  ) : null}
                </div>
              </div>
            ) : (
              <div className="space-y-10">
                {orderedMessages.map((message) => {
                  const isAssistant = message.role === "assistant";
                  return (
                    <div key={message.id} className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
                      <div className={`max-w-3xl ${isAssistant ? "w-full" : "max-w-2xl"}`}>
                        <div className="mb-2 flex items-center gap-2 text-xs">
                          <span className={isAssistant ? "font-semibold text-[color:var(--text-primary)]" : "font-semibold text-[color:var(--text-muted)]"}>
                            {isAssistant ? "Studify" : "Bạn"}
                          </span>
                          <span className="text-[color:var(--text-soft)]">{formatDateTime(message.created_at)}</span>
                          {visibleReply?.category && isAssistant ? (
                            <span className="rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[10px] text-[color:var(--accent)]">
                              {message.category ?? visibleReply.category}
                            </span>
                          ) : null}
                        </div>
                        {isAssistant ? (
                          <div className="rounded-[26px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-4">
                            <MarkdownContent content={message.content} className="text-sm" />
                          </div>
                        ) : (
                          <div className="inline-flex rounded-[24px] bg-[color:var(--chat-user-bg)] px-5 py-4 text-[color:var(--chat-user-text)] shadow-[0_10px_24px_rgba(40,80,120,0.16)]">
                            <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {showPendingUser ? (
                  <div className="flex justify-end">
                    <div className="max-w-2xl rounded-[24px] bg-[color:var(--chat-user-bg)] px-5 py-4 text-[color:var(--chat-user-text)] shadow-[0_10px_24px_rgba(40,80,120,0.16)]">
                      <div className="mb-2 text-xs text-[color:var(--chat-user-text)]/75">{formatDateTime(pendingUserMessage.createdAt)}</div>
                      <p className="whitespace-pre-wrap text-sm leading-7">{pendingUserMessage.content}</p>
                    </div>
                  </div>
                ) : null}

                {loading && (!streamingReply || !streamingReply.answer.trim()) ? (
                  <div className="flex justify-start">
                    <div className="w-full max-w-3xl">
                      <div className="mb-2 flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
                        <MessageCircleHeart className="h-4 w-4 text-[color:var(--accent)]" />
                        {assistantStatus}
                      </div>
                      <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-4">
                        <div className="thinking-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {streamingReply && streamingReply.answer.trim() ? (
                  <div className="flex justify-start">
                    <div className="w-full max-w-3xl">
                      <div className="mb-2 flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
                        <MessageCircleHeart className="h-4 w-4 text-[color:var(--accent)]" />
                        {assistantStatus || "Studify đang trả lời..."}
                      </div>
                      <div className="rounded-[26px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-4">
                        <MarkdownContent content={streamingReply.answer} className="text-sm" />
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {hasConversation ? (
          <div className="border-t border-[color:var(--line)] bg-[color:var(--page-bg)] px-4 py-4 sm:px-6">
            <div className="mx-auto w-full max-w-4xl">
              {error ? (
                <p className="mb-3 rounded-[16px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
                  {error}
                </p>
              ) : null}
              <ChatComposer content={content} loading={loading} onChange={setContent} onSubmit={() => void handleSend()} />
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
