"use client";
import { useId, useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { GlassPanel } from "./Glass";
import Button from "./Button";

/* ---------------------------------------------------------------- SectionTitle */
export function SectionTitle({ eyebrow, title, children, right, as: As = "h1" }: { eyebrow?: string; title: ReactNode; children?: ReactNode; right?: ReactNode; as?: "h1" | "h2" }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <As className={`mt-2 text-balance ${As === "h1" ? "text-[clamp(1.75rem,3.4vw,2.6rem)]" : "text-2xl"}`}>{title}</As>
        {children && <p className="mt-3 text-[15px] leading-relaxed text-ink-dim [font-variation-settings:'opsz'_20]">{children}</p>}
      </div>
      {right}
    </div>
  );
}

/* ---------------------------------------------------------------- Tag */
export function Tag({ children, active }: { children: ReactNode; active?: boolean }) {
  return <span className={`pill !py-1 !text-[11.5px] ${active ? "!border-mint/50 !text-white" : ""}`}>{children}</span>;
}

/* ---------------------------------------------------------------- Stat (KPI card) */
export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <GlassPanel className="p-5">
      <p className="eyebrow">{label}</p>
      <p className="num mt-3 text-[2.6rem] font-[545] leading-none tracking-[-0.03em] [font-variation-settings:'opsz'_32]">{value}</p>
      {hint && <p className="mt-2 text-xs leading-snug text-ink-mute">{hint}</p>}
    </GlassPanel>
  );
}

/* ---------------------------------------------------------------- DataTable */
export type Col<T> = { key: string; label: string; render?: (row: T, i: number) => ReactNode; className?: string; mono?: boolean };
export function DataTable<T>({ columns, rows, caption, maxHeight = 420, rowKey }: { columns: Col<T>[]; rows: T[]; caption?: string; maxHeight?: number; rowKey?: (r: T, i: number) => string }) {
  return (
    <div className="panel overflow-hidden">
      <div className="overflow-auto" style={{ maxHeight }} tabIndex={0} role="region" aria-label={caption || "Data table"}>
        <table className="w-full min-w-max text-left text-xs">
          {caption && <caption className="sr-only">{caption}</caption>}
          <thead className="sticky top-0 z-10 bg-[#101014]/95 text-ink-dim backdrop-blur">
            <tr>{columns.map((c) => <th key={c.key} scope="col" className="whitespace-nowrap px-3 py-2.5 font-medium">{c.label}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {rows.map((r, i) => (
              <tr key={rowKey ? rowKey(r, i) : i} className="transition-colors hover:bg-white/[.05]">
                {columns.map((c) => (
                  <td key={c.key} className={`px-3 py-2 align-top text-ink-dim ${c.mono ? "whitespace-nowrap font-mono" : ""} ${c.className || ""}`}>
                    {c.render ? c.render(r, i) : String((r as Record<string, unknown>)[c.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Tabs */
export function Tabs({ tabs, value, onChange, label = "Sections" }: { tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void; label?: string }) {
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, i: number) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const n = (i + d + tabs.length) % tabs.length;
    refs.current[n]?.focus();
    onChange(tabs[n].id);
  };
  return (
    <div role="tablist" aria-label={label} className="flex max-w-full gap-1 overflow-x-auto rounded-btn border border-line bg-white/[.06] p-1">
      {tabs.map((t, i) => (
        <button
          key={t.id} ref={(el) => { refs.current[i] = el; }} id={`${base}-${t.id}`} role="tab" aria-selected={value === t.id} tabIndex={value === t.id ? 0 : -1}
          onClick={() => onChange(t.id)} onKeyDown={(e) => onKey(e, i)}
          className={`shrink-0 whitespace-nowrap rounded-[8px] px-3.5 py-1.5 text-[13px] font-medium tracking-[-0.02em] transition-colors ${value === t.id ? "bg-white text-black" : "text-ink-dim hover:bg-white/10 hover:text-white"}`}
        >{t.label}</button>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- SearchInput */
export function SearchInput({ value, onChange, placeholder, label }: { value: string; onChange: (v: string) => void; placeholder?: string; label: string }) {
  return (
    <div className="relative">
      <svg className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-mute" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden><path d="M11 4a7 7 0 100 14 7 7 0 000-14zm10 17l-5-5" /></svg>
      <input className="input !pl-10" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={label} />
    </div>
  );
}

/* ---------------------------------------------------------------- Tooltip (CSS only, works on hover and keyboard focus) */
export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="group relative inline-flex" tabIndex={0}>
      {children}
      <span role="tooltip" className="pop pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-max max-w-[240px] -translate-x-1/2 px-3 py-2 text-xs leading-snug text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus:opacity-100">{text}</span>
    </span>
  );
}

/* ---------------------------------------------------------------- Skeleton / Empty / Error */
export function Skeleton({ lines = 3, className = "" }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2.5 ${className}`} aria-hidden>
      {Array.from({ length: lines }, (_, i) => <div key={i} className="skeleton h-3.5" style={{ width: `${i === lines - 1 ? 55 : 92 - ((i * 7) % 18)}%` }} />)}
    </div>
  );
}
export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <GlassPanel className="p-10 text-center">
      <p className="text-lg font-[545] [font-variation-settings:'opsz'_22]">{title}</p>
      {hint && <p className="mx-auto mt-1.5 max-w-md text-sm text-ink-dim">{hint}</p>}
    </GlassPanel>
  );
}
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <GlassPanel className="border-warm/40 p-5" role="alert">
      <p className="font-medium text-warm">Something went wrong</p>
      <p className="mt-1 text-sm text-ink-dim">{message}</p>
      {onRetry && <Button size="sm" className="mt-3" onClick={onRetry}>Try again</Button>}
    </GlassPanel>
  );
}

/* ---------------------------------------------------------------- Drawer (right-side glass drawer) */
export function Drawer({ open, onClose, children, label }: { open: boolean; onClose: () => void; children: ReactNode; label: string }) {
  if (!open) return null;
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 xl:hidden" onClick={onClose} aria-hidden />
      <aside
        role="dialog" aria-label={label} onKeyDown={(e) => e.key === "Escape" && onClose()}
        className="pop slide-in fixed inset-y-3 right-3 z-50 flex w-[min(440px,calc(100vw-1.5rem))] flex-col overflow-hidden"
      >
        {children}
      </aside>
    </>
  );
}
