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
  token: string;
  user: StoredUser;
};

const TOKEN_KEY = "studify_access_token";
const USER_KEY = "studify_user";
const THEME_KEY = "studify_theme";

export function saveAuth(auth: StoredAuth) {
  localStorage.setItem(TOKEN_KEY, auth.token);
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
  document.cookie = `studify_access_token=${auth.token}; Path=/; SameSite=Lax`;
}

export function readAuth(): StoredAuth | null {
  if (typeof window === "undefined") {
    return null;
  }
  const token = localStorage.getItem(TOKEN_KEY);
  const userRaw = localStorage.getItem(USER_KEY);
  if (!token || !userRaw) {
    return null;
  }

  try {
    return { token, user: JSON.parse(userRaw) as StoredUser };
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  document.cookie = "studify_access_token=; Path=/; Max-Age=0; SameSite=Lax";
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
