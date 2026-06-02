"use client";

import dynamic from "next/dynamic";

const AppShellInner = dynamic(
  () => import("./app-shell-inner").then((mod) => ({ default: mod.AppShellInner })),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-screen bg-[color:var(--page-bg)] text-[color:var(--text-primary)]" />
    ),
  },
);

export function AppShell(props: React.ComponentProps<typeof AppShellInner>) {
  return <AppShellInner {...props} />;
}
