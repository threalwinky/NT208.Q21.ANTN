"use client";

import { Music, Pencil, Plus, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";
import {
  createMusicPlaylist,
  deleteMusicPlaylist,
  getAdminMusicPlaylists,
  updateMusicPlaylist,
  type MusicPlaylist,
} from "@/lib/api";

const THEMES = [
  { value: "focus", label: "Tập trung" },
  { value: "relax", label: "Thư giãn" },
  { value: "motivation", label: "Động lực" },
  { value: "sleep", label: "Ngủ ngon" },
  { value: "study", label: "Học bài" },
  { value: "stress_relief", label: "Giảm stress" },
];

const EMPTY_FORM: Omit<MusicPlaylist, "id"> = {
  theme: "focus",
  title: "",
  description: "",
  spotify_url: "",
  embed_url: "",
  cover_url: "",
  is_active: true,
};

export default function AdminMusicPlaylistsPage() {
  const [playlists, setPlaylists] = useState<MusicPlaylist[]>([]);
  const [filterTheme, setFilterTheme] = useState<string>("");
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<MusicPlaylist | null>(null);
  const [form, setForm] = useState<Omit<MusicPlaylist, "id">>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function load(theme?: string) {
    setError("");
    try {
      const data = await getAdminMusicPlaylists(theme || undefined);
      setPlaylists(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được danh sách playlist.");
    }
  }

  useEffect(() => {
    void load(filterTheme || undefined);
  }, [filterTheme]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(item: MusicPlaylist) {
    setEditing(item);
    setForm({
      theme: item.theme,
      title: item.title,
      description: item.description ?? "",
      spotify_url: item.spotify_url ?? "",
      embed_url: item.embed_url ?? "",
      cover_url: item.cover_url ?? "",
      is_active: item.is_active,
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  async function handleSave() {
    if (!form.title.trim() || !form.theme) {
      setError("Chủ đề và tiêu đề không được để trống.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...form,
        description: form.description || null,
        spotify_url: form.spotify_url || null,
        embed_url: form.embed_url || null,
        cover_url: form.cover_url || null,
      };
      if (editing) {
        await updateMusicPlaylist(editing.id, payload);
      } else {
        await createMusicPlaylist(payload);
      }
      closeForm();
      await load(filterTheme || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id);
    setError("");
    try {
      await deleteMusicPlaylist(id);
      await load(filterTheme || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xóa thất bại.");
    } finally {
      setDeletingId(null);
    }
  }

  const themeLabel = (value: string) => THEMES.find((t) => t.value === value)?.label ?? value;

  return (
    <AppShell
      pageTitle="Quản lý playlist nhạc"
      pageDescription="Thêm, sửa, xóa playlist nhạc gợi ý cho sinh viên trong module wellbeing. Mỗi playlist gắn với một chủ đề cảm xúc khác nhau."
    >
      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-[color:var(--text-muted)]">Lọc theo chủ đề:</span>
          <button
            type="button"
            onClick={() => setFilterTheme("")}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              filterTheme === ""
                ? "bg-[color:var(--accent)] text-white"
                : "border border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-primary)] hover:bg-[color:var(--accent-soft)]"
            }`}
          >
            Tất cả
          </button>
          {THEMES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setFilterTheme(t.value)}
              className={`rounded-md px-3 py-1.5 text-sm transition ${
                filterTheme === t.value
                  ? "bg-[color:var(--accent)] text-white"
                  : "border border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--text-primary)] hover:bg-[color:var(--accent-soft)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="btn-primary inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold"
        >
          <Plus className="h-4 w-4" />
          Thêm playlist
        </button>
      </div>

      {showForm ? (
        <AppCard
          title={editing ? "Sửa playlist" : "Thêm playlist mới"}
          subtitle="Điền thông tin playlist nhạc gợi ý theo chủ đề wellbeing."
          action={
            <button type="button" onClick={closeForm} className="rounded-md p-2 hover:bg-[color:var(--surface-soft)]">
              <X className="h-4 w-4" />
            </button>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[color:var(--text-primary)]">Chủ đề *</label>
              <select
                value={form.theme}
                onChange={(e) => setForm((prev) => ({ ...prev, theme: e.target.value }))}
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              >
                {THEMES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[color:var(--text-primary)]">Tiêu đề *</label>
              <input
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                placeholder="VD: Lo-fi beats for deep focus"
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-sm font-medium text-[color:var(--text-primary)]">Mô tả</label>
              <input
                value={form.description ?? ""}
                onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Mô tả ngắn về playlist"
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[color:var(--text-primary)]">Spotify URL</label>
              <input
                value={form.spotify_url ?? ""}
                onChange={(e) => setForm((prev) => ({ ...prev, spotify_url: e.target.value }))}
                placeholder="https://open.spotify.com/playlist/..."
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[color:var(--text-primary)]">Embed URL</label>
              <input
                value={form.embed_url ?? ""}
                onChange={(e) => setForm((prev) => ({ ...prev, embed_url: e.target.value }))}
                placeholder="https://open.spotify.com/embed/playlist/..."
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[color:var(--text-primary)]">Cover URL</label>
              <input
                value={form.cover_url ?? ""}
                onChange={(e) => setForm((prev) => ({ ...prev, cover_url: e.target.value }))}
                placeholder="https://..."
                className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm outline-none"
              />
            </div>
            <div className="flex items-end">
              <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                />
                Hiển thị cho sinh viên
              </label>
            </div>
          </div>
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="btn-primary inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
            >
              {saving ? "Đang lưu..." : editing ? "Cập nhật" : "Tạo playlist"}
            </button>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-5 py-2.5 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[color:var(--surface)]"
            >
              Hủy
            </button>
          </div>
        </AppCard>
      ) : null}

      <AppCard
        title={`Danh sách playlist${filterTheme ? ` — ${themeLabel(filterTheme)}` : ""}`}
        subtitle={`${playlists.length} playlist${playlists.length !== 1 ? "" : ""} đã cấu hình`}
      >
        <div className="space-y-3">
          {playlists.map((item) => (
            <div
              key={item.id}
              className="rounded-lg border border-[color:var(--line)] bg-[color:var(--surface-soft)] p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-[color:var(--accent-soft)]">
                    {item.cover_url ? (
                      <img
                        src={item.cover_url}
                        alt={item.title}
                        className="h-10 w-10 rounded-[14px] object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <Music className="h-5 w-5 text-[color:var(--accent)]" />
                    )}
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{item.title}</p>
                      <Badge tone={item.is_active ? "success" : "warn"}>
                        {item.is_active ? "Đang hiện" : "Ẩn"}
                      </Badge>
                      <Badge tone="default">{themeLabel(item.theme)}</Badge>
                    </div>
                    {item.description ? (
                      <p className="mt-1.5 text-sm text-[color:var(--text-muted)]">{item.description}</p>
                    ) : null}
                    {item.spotify_url ? (
                      <a
                        href={item.spotify_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1.5 block truncate text-xs text-[color:var(--accent)] hover:underline"
                      >
                        {item.spotify_url}
                      </a>
                    ) : null}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    onClick={() => openEdit(item)}
                    className="inline-flex items-center gap-1.5 rounded-md border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-xs font-medium text-[color:var(--text-primary)] transition hover:bg-[color:var(--accent-soft)]"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Sửa
                  </button>
                  <button
                    type="button"
                    disabled={deletingId === item.id}
                    onClick={() => void handleDelete(item.id)}
                    className="inline-flex items-center gap-1.5 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700 transition hover:bg-red-100 disabled:opacity-60 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    {deletingId === item.id ? "Đang xóa..." : "Xóa"}
                  </button>
                </div>
              </div>
              {item.embed_url ? (
                <div className="mt-4 overflow-hidden rounded-md">
                  <iframe
                    src={item.embed_url}
                    width="100%"
                    height="80"
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    loading="lazy"
                    className="rounded-md"
                  />
                </div>
              ) : null}
            </div>
          ))}
          {!playlists.length ? (
            <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-6 text-center">
              <Music className="mx-auto mb-3 h-8 w-8 text-[color:var(--text-muted)]" />
              <p className="text-sm text-[color:var(--text-muted)]">
                {filterTheme ? `Chưa có playlist nào cho chủ đề "${themeLabel(filterTheme)}".` : "Chưa có playlist nào. Nhấn \"Thêm playlist\" để bắt đầu."}
              </p>
            </div>
          ) : null}
        </div>
      </AppCard>
    </AppShell>
  );
}
