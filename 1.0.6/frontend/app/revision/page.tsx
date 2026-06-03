"use client";

import { FileText, Loader2, Plus, Send, Sparkles, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui";
import { MarkdownContent } from "@/components/markdown-content";
import {
  askNotebook,
  createNotebook,
  deleteNotebook,
  deleteNotebookDocument,
  getNotebook,
  getNotebooks,
  uploadNotebookDocument,
  type Notebook,
  type NotebookDetail,
  type RevisionAnswer,
} from "@/lib/api";

function statusBadge(status: string) {
  if (status === "READY") return <Badge tone="success">Sẵn sàng</Badge>;
  if (status === "FAILED") return <Badge tone="danger">Lỗi</Badge>;
  return <Badge tone="accent">Đang xử lý...</Badge>;
}

export default function RevisionPage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<NotebookDetail | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<RevisionAnswer | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadNotebooks(selectFirst = false) {
    const list = await getNotebooks();
    setNotebooks(list);
    if (selectFirst && list.length && selectedId === null) {
      void selectNotebook(list[0].id);
    }
  }

  async function selectNotebook(id: number) {
    setSelectedId(id);
    setAnswer(null);
    setError("");
    try {
      setDetail(await getNotebook(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được sổ.");
    }
  }

  useEffect(() => {
    void loadNotebooks(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate() {
    const title = newTitle.trim();
    if (!title || creating) return;
    setCreating(true);
    setError("");
    try {
      const nb = await createNotebook(title);
      setNewTitle("");
      await loadNotebooks();
      void selectNotebook(nb.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tạo được sổ.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteNotebook(id: number) {
    if (!confirm("Xoá sổ này cùng toàn bộ tài liệu đã tải lên?")) return;
    await deleteNotebook(id);
    if (selectedId === id) {
      setSelectedId(null);
      setDetail(null);
      setAnswer(null);
    }
    await loadNotebooks();
  }

  async function handleUpload(file: File) {
    if (!selectedId || uploading) return;
    setUploading(true);
    setError("");
    try {
      await uploadNotebookDocument(selectedId, file);
      setDetail(await getNotebook(selectedId));
      await loadNotebooks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được tài liệu.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleDeleteDoc(docId: number) {
    if (!selectedId) return;
    await deleteNotebookDocument(selectedId, docId);
    setDetail(await getNotebook(selectedId));
    await loadNotebooks();
  }

  async function handleAsk() {
    const q = question.trim();
    if (!q || !selectedId || asking) return;
    setAsking(true);
    setError("");
    setAnswer(null);
    try {
      setAnswer(await askNotebook(selectedId, q));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không hỏi được.");
    } finally {
      setAsking(false);
    }
  }

  const readyCount = detail?.documents.filter((d) => d.status === "READY").length ?? 0;

  return (
    <AppShell
      pageTitle="Ôn tập"
      pageDescription="Tải tài liệu PDF của riêng bạn, Studify chỉ trả lời dựa trên đúng tài liệu trong từng sổ — như một trợ lý ôn thi cá nhân."
    >
      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        {/* ── Cột sổ ôn tập ── */}
        <aside className="space-y-4">
          <div className="card-soft p-4">
            <p className="mb-2 text-sm font-semibold">Tạo sổ mới</p>
            <div className="flex gap-2">
              <input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                placeholder="Ví dụ: Giải tích 1"
                className="min-w-0 flex-1 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-sm outline-none focus:border-[color:var(--accent)]"
              />
              <button
                type="button"
                onClick={handleCreate}
                disabled={creating || !newTitle.trim()}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[color:var(--accent)] text-white transition hover:bg-[color:var(--accent-strong)] disabled:opacity-60"
              >
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {notebooks.length === 0 ? (
              <p className="px-1 text-sm text-[color:var(--text-muted)]">Chưa có sổ nào. Tạo một sổ để bắt đầu ôn tập.</p>
            ) : (
              notebooks.map((nb) => {
                const active = nb.id === selectedId;
                return (
                  <div
                    key={nb.id}
                    className={`group flex items-center justify-between gap-2 rounded-xl border px-3 py-2.5 transition ${
                      active
                        ? "border-[color:var(--accent)] bg-[color:var(--accent-soft)]"
                        : "border-[color:var(--line)] bg-[color:var(--surface)] hover:border-[color:var(--accent)]"
                    }`}
                  >
                    <button type="button" onClick={() => void selectNotebook(nb.id)} className="min-w-0 flex-1 text-left">
                      <p className="truncate text-sm font-medium">{nb.title}</p>
                      <p className="text-xs text-[color:var(--text-soft)]">
                        {nb.ready_count}/{nb.document_count} tài liệu sẵn sàng
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteNotebook(nb.id)}
                      title="Xoá sổ"
                      className="shrink-0 rounded-md p-1 text-[color:var(--text-soft)] opacity-0 transition hover:text-rose-500 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* ── Cột nội dung ── */}
        <section className="min-w-0 space-y-5">
          {!detail ? (
            <div className="card-soft flex flex-col items-center justify-center gap-3 p-12 text-center">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                <Sparkles className="h-6 w-6" />
              </span>
              <p className="text-base font-semibold">Chọn hoặc tạo một sổ ôn tập</p>
              <p className="max-w-md text-sm text-[color:var(--text-muted)]">
                Mỗi sổ là một không gian riêng. Tải PDF (bài giảng, giáo trình, đề cương) rồi hỏi Studify — câu trả lời
                chỉ dựa trên tài liệu trong sổ đó.
              </p>
            </div>
          ) : (
            <>
              {/* Tài liệu */}
              <div className="card-soft p-5">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">{detail.title}</h2>
                    <p className="mt-1 text-sm text-[color:var(--text-muted)]">{detail.documents.length} tài liệu PDF</p>
                  </div>
                  <label
                    className={`inline-flex cursor-pointer items-center gap-2 rounded-lg bg-[color:var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[color:var(--accent-strong)] ${
                      uploading ? "pointer-events-none opacity-70" : ""
                    }`}
                  >
                    {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    {uploading ? "Đang xử lý..." : "Tải PDF"}
                    <input
                      ref={fileRef}
                      type="file"
                      accept="application/pdf,.pdf"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) void handleUpload(f);
                      }}
                    />
                  </label>
                </div>

                {detail.documents.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-8 text-center text-sm text-[color:var(--text-muted)]">
                    Chưa có tài liệu. Tải lên một file PDF để Studify học nội dung.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {detail.documents.map((doc) => (
                      <li
                        key={doc.id}
                        className="flex items-center justify-between gap-3 rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-2.5"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <FileText className="h-5 w-5 shrink-0 text-[color:var(--accent)]" />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium" title={doc.title}>
                              {doc.title}
                            </p>
                            <p className="text-xs text-[color:var(--text-soft)]">
                              {doc.status === "READY"
                                ? `${doc.chunk_count} đoạn${doc.used_ocr ? " • OCR" : ""}`
                                : doc.error || "Đang trích xuất nội dung..."}
                            </p>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          {statusBadge(doc.status)}
                          <button
                            type="button"
                            onClick={() => void handleDeleteDoc(doc.id)}
                            title="Xoá tài liệu"
                            className="rounded-md p-1 text-[color:var(--text-soft)] transition hover:text-rose-500"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Hỏi đáp */}
              <div className="card-soft p-5">
                <h3 className="text-base font-semibold tracking-tight">Hỏi về tài liệu</h3>
                <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                  Studify chỉ trả lời dựa trên {readyCount > 0 ? `${readyCount} tài liệu sẵn sàng` : "tài liệu trong sổ này"}, không dùng nguồn ngoài.
                </p>

                <div className="mt-4 flex items-end gap-2">
                  <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void handleAsk();
                      }
                    }}
                    rows={1}
                    placeholder="Ví dụ: Tóm tắt chương 2 giúp mình..."
                    className="min-h-[44px] max-h-[160px] flex-1 resize-none rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2.5 text-sm outline-none focus:border-[color:var(--accent)]"
                  />
                  <button
                    type="button"
                    onClick={handleAsk}
                    disabled={asking || !question.trim() || readyCount === 0}
                    className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[color:var(--accent)] text-white transition hover:bg-[color:var(--accent-strong)] disabled:opacity-60"
                  >
                    {asking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </button>
                </div>

                {asking ? (
                  <p className="mt-4 text-sm text-[color:var(--text-muted)]">Studify đang đọc tài liệu của bạn...</p>
                ) : answer ? (
                  <div className="mt-5 space-y-4">
                    <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4">
                      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--accent)]">
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-[color:var(--accent)] text-white">
                          <Sparkles className="h-3.5 w-3.5" />
                        </span>
                        Studify trả lời
                      </div>
                      <MarkdownContent content={answer.answer} className="text-sm" />
                    </div>
                    {answer.citations.length > 0 ? (
                      <div>
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--text-soft)]">
                          Trích từ tài liệu
                        </p>
                        <div className="grid gap-2 sm:grid-cols-2">
                          {answer.citations.map((c, i) => (
                            <div key={i} className="rounded-xl border border-[color:var(--line)] bg-[color:var(--surface)] p-3">
                              <p className="flex items-center gap-1.5 text-xs font-semibold text-[color:var(--accent)]">
                                <FileText className="h-3.5 w-3.5" /> {c.doc_title}
                              </p>
                              <p className="mt-1 line-clamp-3 text-xs leading-5 text-[color:var(--text-muted)]">{c.excerpt}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </>
          )}
        </section>
      </div>
    </AppShell>
  );
}
