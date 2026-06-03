import type { ReactNode } from "react";

export function AppCard({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-6 shadow-[var(--shadow-card)] ${className}`}>
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">{title}</h2>
          {subtitle ? <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-muted)]">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-6 shadow-[var(--shadow-card)]">
      <p className="text-sm text-[color:var(--text-muted)]">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)]">{value}</p>
      <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[color:var(--text-soft)]">{hint}</p>
    </div>
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "accent" | "warn" | "danger" | "success";
}) {
  const tones = {
    default: "bg-[color:var(--badge-default-bg)] text-[color:var(--badge-default-text)] border-[color:var(--badge-default-border)]",
    accent: "bg-[color:var(--badge-accent-bg)] text-[color:var(--badge-accent-text)] border-[color:var(--badge-accent-border)]",
    warn: "bg-[color:var(--badge-warn-bg)] text-[color:var(--badge-warn-text)] border-[color:var(--badge-warn-border)]",
    danger: "bg-[color:var(--badge-danger-bg)] text-[color:var(--badge-danger-text)] border-[color:var(--badge-danger-border)]",
    success: "bg-[color:var(--badge-success-bg)] text-[color:var(--badge-success-text)] border-[color:var(--badge-success-border)]",
  } as const;

  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
