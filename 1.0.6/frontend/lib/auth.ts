"use client";

export type StoredUser = {
  id: number;
  username: string;
  full_name: string;
  role: string;
  email?: string | null;
  student_id?: string | null;
};

export type StoredAuth = {
  user: StoredUser;
};

const USER_KEY = "studify_user";
const THEME_KEY = "studify_theme";

export function saveAuth(auth: StoredAuth) {
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
}

export function readAuth(): StoredAuth | null {
  if (typeof window === "undefined") {
    return null;
  }
  const userRaw = localStorage.getItem(USER_KEY);
  if (!userRaw) {
    return null;
  }

  try {
    return { user: JSON.parse(userRaw) as StoredUser };
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(USER_KEY);
  document.cookie = "studify_access_token=; Path=/; Max-Age=0; SameSite=Lax";
  document.cookie = "studify_session=; Path=/; Max-Age=0; SameSite=Lax";
}

export function saveTheme(theme: "dark" | "light") {
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.dataset.theme = theme;
}

export function loadTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  const theme = stored === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  return theme;
}
