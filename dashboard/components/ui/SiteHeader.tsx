"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Wordmark } from "../Logo";
import Button from "./Button";

const LINKS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/explorer", label: "Explorer", also: ["/investigations", "/compare"] },
  { href: "/assistant", label: "Assistant" },
  { href: "/data", label: "Data" },
  { href: "/insights", label: "Insights" },
];

/** Same bar as the landing page: brand, five links, ghost + solid buttons, mobile menu sheet. Sticky. */
export default function SiteHeader() {
  const path = usePathname() || "";
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLElement>(null);
  const isActive = (l: (typeof LINKS)[number]) => path === l.href || (l.href !== "/dashboard" && path.startsWith(l.href)) || !!l.also?.some((a) => path.startsWith(a));

  useEffect(() => { setOpen(false); }, [path]);
  useEffect(() => {
    const click = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", click);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("click", click); document.removeEventListener("keydown", key); };
  }, []);

  return (
    <header ref={ref} className="no-print sticky top-0 z-40 border-b border-line bg-black/55 [-webkit-backdrop-filter:blur(14px)_saturate(140%)] [backdrop-filter:blur(14px)_saturate(140%)]">
      <div className="relative mx-auto flex h-[60px] w-full max-w-[1280px] items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link href="/" aria-label="FlameIntel — home" className="shrink-0"><Wordmark /></Link>

        <nav className="ml-6 hidden items-center gap-1 lg:flex" aria-label="Primary">
          {LINKS.map((l) => (
            <Link
              key={l.href} href={l.href} aria-current={isActive(l) ? "page" : undefined}
              className={`rounded-full px-3.5 py-1.5 text-[13px] tracking-[-0.025em] transition-colors [font-variation-settings:'opsz'_15] ${isActive(l) ? "bg-white/[.14] font-medium text-white" : "text-ink-nav hover:text-white"}`}
            >{l.label}</Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Button href="/about">Data notes</Button>
          <Button href="/report" variant="solid" className="hidden lg:inline-flex">Report</Button>
          <button
            type="button" aria-label={open ? "Close menu" : "Menu"} aria-expanded={open} aria-controls="menu-sheet"
            onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
            className="inline-flex h-9 w-9 items-center justify-center rounded-btn border border-white/35 text-white transition-colors hover:bg-white/10 lg:hidden"
          >
            <svg viewBox="0 0 20 14" width="55%" height="55%" fill="none" aria-hidden><path d="M0 1h20M0 7h20M0 13h20" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
        </div>

        {open && (
          <nav id="menu-sheet" aria-label="Menu" className="pop slide-in absolute right-4 top-[calc(100%+9px)] min-w-[210px] p-2.5 sm:right-6 lg:hidden">
            {[...LINKS, { href: "/compare", label: "Compare" }].map((l) => (
              <Link key={l.href} href={l.href} className="block rounded-[9px] px-2.5 py-2 text-sm tracking-[-0.025em] text-ink-nav [font-variation-settings:'opsz'_15] hover:bg-white/[.08] hover:text-white">{l.label}</Link>
            ))}
            <Button href="/report" variant="solid" className="mt-2 !flex !h-[38px] w-full">Report</Button>
          </nav>
        )}
      </div>
    </header>
  );
}
