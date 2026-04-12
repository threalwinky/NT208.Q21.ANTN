"use client";

import { MoonStar, SunMedium } from "lucide-react";
import { useState } from "react";

import { saveTheme } from "@/lib/auth";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") {
      return "light";
    }
    const stored = localStorage.getItem("studify_theme");
    const nextTheme = stored === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = nextTheme;
    return nextTheme;
  });

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    saveTheme(nextTheme);
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex h-12 w-12 items-center justify-center rounded-[18px] border border-[color:var(--line)] bg-[color:var(--button-secondary-bg)] text-[color:var(--text-primary)] transition hover:bg-[color:var(--button-secondary-hover)]"
      aria-label="Chuyển chế độ sáng tối"
    >
      {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
    </button>
  );
}
