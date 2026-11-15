"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import HeroScene from "./HeroScene";
import Astronaut from "./Astronaut";
import { Wordmark } from "../Logo";
import { api } from "@/lib/api";

type Stats = { investigations: number; indexed_chunks: number } | null;

export default function Hero() {
  const astroRef = useRef<HTMLDivElement>(null);
  const [stats, setStats] = useState<Stats>(null);
  useEffect(() => {
    api<{ coverage: { investigations: number; indexed_chunks: number } }>("/api/coverage", { timeoutMs: 6000 })
      .then((r) => setStats(r.coverage)).catch(() => setStats(null));
  }, []);

  return (
    <section className="relative isolate h-screen min-h-[640px] w-full overflow-hidden bg-void">
      {/* nebula layers (pure CSS) */}
      <div className="pointer-events-none absolute inset-0 -z-10" aria-hidden>
        <div className="absolute -left-1/4 top-[-20%] h-[90%] w-[80%] rounded-full bg-[radial-gradient(closest-side,rgba(60,50,140,.38),transparent)] blur-2xl" />
        <div className="absolute -right-1/4 bottom-[-30%] h-[100%] w-[85%] rounded-full bg-[radial-gradient(closest-side,rgba(194,65,12,.22),transparent)] blur-2xl" />
        <div className="absolute left-[30%] top-[40%] h-[60%] w-[50%] rounded-full bg-[radial-gradient(closest-side,rgba(40,90,180,.16),transparent)] blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,rgba(2,3,8,.8))]" />
      </div>

      <HeroScene astroRef={astroRef} />

      {/* drifting astronaut */}
      <div
        ref={astroRef}
        className="pointer-events-none absolute bottom-[4%] right-[3%] w-[min(30vw,330px)] max-md:bottom-[2%] max-md:right-[-4%] max-md:w-[46vw]"
        style={{ transform: "translate3d(calc(var(--px,0) * 1px), calc(var(--py,0) * 1px), 0)" }}
      >
        <div className="animate-[astro_28s_ease-in-out_infinite] drop-shadow-[0_0_40px_rgba(255,107,31,.25)]">
          <Astronaut className="h-auto w-full" />
        </div>
      </div>

      {/* top bar */}
      <header className="absolute inset-x-0 top-0 z-10 flex items-center justify-between px-6 py-5 md:px-10">
        <Wordmark />
        <nav className="flex items-center gap-1 text-sm text-ink-dim" aria-label="Landing">
          <Link href="/dashboard" className="rounded-lg px-3 py-1.5 hover:text-ink">Dashboard</Link>
          <Link href="/assistant" className="rounded-lg px-3 py-1.5 hover:text-ink">Assistant</Link>
          <Link href="/about" className="hidden rounded-lg px-3 py-1.5 hover:text-ink sm:block">About the data</Link>
        </nav>
      </header>

      {/* copy */}
      <div className="relative z-10 flex h-full flex-col justify-end px-6 pb-28 md:justify-center md:px-10 md:pb-0 lg:pl-[8vw]">
        <div className="max-w-[640px] animate-rise">
          <p className="eyebrow !text-ember-glow/90">NASA Space Apps 2026 · Flame in Freefall</p>
          <h1 className="h-display mt-4 text-[clamp(3.6rem,10vw,8.2rem)] font-semibold leading-[0.9] tracking-[-0.025em]">
            Flame<span className="bg-gradient-to-b from-ember-glow to-ember bg-clip-text text-transparent">Intel</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-dim md:text-xl">
            Transforms NASA PSI combustion research into a searchable, explainable, and data-aware fire-safety research dashboard for future space habitats and potential terrestrial applications.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/dashboard" className="btn-primary !px-6 !py-3 text-base">
              Enter dashboard
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12h14M13 6l6 6-6 6" /></svg>
            </Link>
            <Link href="/assistant" className="btn-ghost !px-6 !py-3 text-base backdrop-blur">Ask the assistant</Link>
          </div>
        </div>
      </div>

      {/* scroll cue */}
      <a href="#about" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: window.innerHeight, behavior: "smooth" }); }}
        className="absolute bottom-16 left-1/2 z-10 hidden -translate-x-1/2 flex-col items-center gap-1 text-[11px] uppercase tracking-[.2em] text-ink-mute transition hover:text-ink md:flex">
        Learn more
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden><path d="M6 9l6 6 6-6" /></svg>
      </a>

      {/* facts strip (real numbers from the index when the API is up) */}
      <div className="absolute inset-x-0 bottom-0 z-10 border-t border-line/60 bg-void/55 px-6 py-3 backdrop-blur md:px-10">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-1 font-mono text-[11px] uppercase tracking-[.14em] text-ink-mute">
          <span><b className="text-ink">{stats?.investigations ?? "24"}</b> NASA PSI investigations</span>
          <span><b className="text-ink">{(stats?.indexed_chunks ?? 13112).toLocaleString("en-US")}</b> indexed passages</span>
          <span className="text-ink-mute">Every answer cites its source</span>
          <span className="ml-auto hidden text-ink-mute md:inline">Organizes existing research · not a NASA product · no certification</span>
        </div>
      </div>
    </section>
  );
}
