"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EvidenceLabel } from "../Badges";
import { Wordmark } from "../Logo";
import { api } from "@/lib/api";

/** fades a block in once when it scrolls into view (instantly visible with reduced motion) */
function Reveal({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setOn(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setOn(true); io.disconnect(); } }, { threshold: 0.12 });
    if (ref.current) io.observe(ref.current);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className={`transition duration-700 ease-out ${on ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0"} ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function Head({ eyebrow, title, children }: { eyebrow: string; title: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="max-w-3xl">
      <p className="eyebrow !text-ember-glow/90">{eyebrow}</p>
      <h2 className="h-display mt-3 text-[clamp(1.9rem,4vw,3rem)] font-semibold leading-[1.05]">{title}</h2>
      {children && <p className="mt-4 text-base leading-relaxed text-ink-dim md:text-lg">{children}</p>}
    </div>
  );
}

const OBJECTIVES = [
  { n: "01", t: "Find the relevant research", d: "Search and filter 24 NASA PSI combustion investigations by topic, platform and data availability. Pick a scenario and each result is ranked with a plain-language reason, including when the experiment ran in microgravity rather than lunar gravity.", href: "/explorer", cta: "Open the Explorer" },
  { n: "02", t: "See if the data is usable", d: "Inspect the real CSV and Excel files: actual columns, types, documented units, missing values and a preview. A readiness checklist says when there is not enough suitable data for reliable prediction, instead of inventing one.", href: "/data", cta: "Open the Data Explorer" },
  { n: "03", t: "Connect it to fire safety", d: "Cited insights on suppression, smoke detection, fire-resistant materials, crew protection, monitoring and terrestrial uses. Each one carries its limitations and says that validation is required.", href: "/insights", cta: "Read the insights" },
];

const STEPS = [
  ["Import", "NASA PSI records, reports, papers and data tables."],
  ["Split", "13,112 searchable passages from 24 experiments."],
  ["Retrieve", "The passages closest to your question are found."],
  ["Answer", "A language model writes only from those passages."],
  ["Cite", "Every sentence links to its exact source. If the data does not cover it, the assistant says so."],
];

const PAGES = [
  ["Overview", "/dashboard", "Scenario selector, KPIs and charts from the real records."],
  ["Explorer", "/explorer", "Ranked results with a “Why relevant?” explanation."],
  ["Assistant", "/assistant", "Ask in plain language, get cited answers."],
  ["Data Explorer", "/data", "Columns, units, missing values, CSV export."],
  ["Insights", "/insights", "Evidence-labelled fire-safety themes."],
  ["Compare", "/compare", "Qualitative comparison of 2 to 3 studies."],
  ["Report", "/report", "A printable cited report for your scenario."],
  ["About the data", "/about", "What is covered, and what is not."],
];

const SCENARIOS = ["Spacecraft", "ISS", "Lunar Habitat", "Mars Habitat", "Pressurized Rover"];

export default function Sections() {
  const [n, setN] = useState<{ investigations: number; indexed_chunks: number; skipped_files_total: number } | null>(null);
  useEffect(() => {
    api<{ coverage: { investigations: number; indexed_chunks: number; skipped_files_total: number } }>("/api/coverage", { timeoutMs: 6000 }).then((r) => setN(r.coverage)).catch(() => {});
  }, []);

  return (
    <div className="relative bg-void">
      <div className="mx-auto max-w-6xl space-y-28 px-6 py-24 md:px-10 md:py-32">
        {/* what it is */}
        <Reveal>
          <Head eyebrow="What is FlameIntel" title={<>A research dashboard for <span className="text-ember">fire safety in space</span></>}>
            Fire behaves differently in microgravity: flames turn into balls, smoke moves unlike on Earth, and the ordinary rules of thumb stop applying. NASA has run combustion experiments on the ISS for years.
            FlameIntel brings those NASA Physical Sciences Informatics (PSI) investigations, their publications and their accessible data into one place, so a researcher can find, read and check them quickly.
          </Head>
          <p className="mt-4 max-w-3xl rounded-lg border border-line bg-space-800/70 px-4 py-3 text-sm text-ink-dim">
            It organizes existing research. It does not run experiments, replace NASA sources, or certify equipment, and it never presents a prediction or a safety probability.
          </p>
        </Reveal>

        {/* the challenge */}
        <Reveal>
          <div className="grid items-center gap-10 md:grid-cols-[1.1fr_1fr]">
            <Head eyebrow="The challenge · Flame in Freefall" title="Great data, hard to use">
              Future habitats on the Moon and Mars and the ISS need fire-safety knowledge that Earth testing cannot give. The research exists, but it is scattered across records, PDFs and spreadsheets with different units and conditions.
              FlameIntel makes it discoverable, explainable and data-aware, with the source one click away.
            </Head>
            <div className="grid grid-cols-2 gap-3">
              {[[n?.investigations ?? 24, "NASA PSI investigations"], [(n?.indexed_chunks ?? 13112).toLocaleString("en-US"), "indexed passages"], ["5", "scenarios to rank for"], ["100%", "answers cite a source"]].map(([v, l]) => (
                <div key={String(l)} className="card p-4">
                  <p className="h-display text-4xl font-semibold text-ember-glow">{v}</p>
                  <p className="mt-1 text-xs text-ink-mute">{l}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>

        {/* three objectives */}
        <div>
          <Reveal><Head eyebrow="What you can do" title="Three questions, answered with evidence" /></Reveal>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {OBJECTIVES.map((o, i) => (
              <Reveal key={o.n} delay={i * 120}>
                <div className="card flex h-full flex-col p-6 transition hover:border-ember/40">
                  <span className="font-mono text-sm text-ember">{o.n}</span>
                  <h3 className="h-display mt-3 text-2xl font-semibold leading-snug">{o.t}</h3>
                  <p className="mt-3 flex-1 text-sm leading-relaxed text-ink-dim">{o.d}</p>
                  <Link href={o.href} className="mt-5 text-sm text-ember-glow hover:underline">{o.cta} →</Link>
                </div>
              </Reveal>
            ))}
          </div>
        </div>

        {/* scenarios */}
        <Reveal>
          <Head eyebrow="Scenario-based ranking" title="Pick where the crew will be">
            Choose Spacecraft, ISS, Lunar Habitat, Mars Habitat or Pressurized Rover. FlameIntel ranks the investigations by topic fit, platform fit, data availability and source coverage, and explains every score.
          </Head>
          <div className="mt-6 flex flex-wrap gap-2">
            {SCENARIOS.map((s) => <span key={s} className="chip !border-ember/30 !px-4 !py-1.5 !text-sm !text-ink">{s}</span>)}
          </div>
          <p className="mt-4 max-w-3xl rounded-lg border border-warn/30 bg-warn/5 px-4 py-3 text-sm text-ink-dim">
            <b className="text-warn">Honest by design: </b>the score is an app-generated aid, not an official NASA rating. If an experiment ran in microgravity, the card says that microgravity is not lunar gravity.
          </p>
        </Reveal>

        {/* RAG */}
        <Reveal>
          <Head eyebrow="The AI assistant" title="Answers that show their work">
            Retrieval-augmented generation: the assistant retrieves passages first and writes only from them. It abstains when the evidence is missing and never invents an experiment or a result.
          </Head>
          <ol className="mt-8 grid gap-3 md:grid-cols-5">
            {STEPS.map(([t, d], i) => (
              <li key={t} className="card relative p-4">
                <span className="font-mono text-xs text-ember">{String(i + 1).padStart(2, "0")}</span>
                <p className="h-display mt-1 text-lg font-semibold">{t}</p>
                <p className="mt-1 text-xs leading-relaxed text-ink-mute">{d}</p>
              </li>
            ))}
          </ol>
          <div className="card mt-6 space-y-3 p-5 text-sm">
            <p className="eyebrow">Example</p>
            <p className="rounded-lg bg-space-600/60 px-3 py-2">What channels did the SAFFIRE smoke detector record?</p>
            <p className="leading-relaxed text-ink-dim">
              <span className="mr-1.5 rounded border border-ok/40 bg-ok/10 px-1.5 py-px font-mono text-[11px] uppercase text-ok">Observed</span>
              Telemetry data recorded channels for smoke detector obscuration (V) and scatterometer (V)
              <span className="mx-0.5 rounded border border-ember/40 bg-ember/10 px-1.5 font-mono text-[11px] text-ember-glow">S1</span>
              <span className="mx-0.5 rounded border border-ember/40 bg-ember/10 px-1.5 font-mono text-[11px] text-ember-glow">S3</span>
              <span className="ml-2 text-xs text-ink-mute">← click a tag to open the exact source passage</span>
            </p>
          </div>
        </Reveal>

        {/* evidence labels */}
        <Reveal>
          <Head eyebrow="Traceability" title="Facts, interpretation and possibility never get mixed">
            Every page separates what a NASA source states from what the app infers and from what might be possible later.
          </Head>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {([["source_reported", "Stated in a NASA PSI source, with a citation you can open."], ["app_interpretation", "FlameIntel's own relevance analysis. Not a NASA statement."], ["potential_application", "A possible future use that needs validation. Never a certification."]] as const).map(([k, d]) => (
              <div key={k} className="card space-y-3 p-5"><EvidenceLabel kind={k} /><p className="text-sm text-ink-dim">{d}</p></div>
            ))}
          </div>
        </Reveal>

        {/* pages */}
        <div>
          <Reveal><Head eyebrow="Inside the dashboard" title="Eight pages, one workflow" /></Reveal>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {PAGES.map(([t, h, d], i) => (
              <Reveal key={t} delay={(i % 4) * 80}>
                <Link href={h} className="card group block h-full p-4 transition hover:border-ember/50 hover:bg-space-700/80">
                  <p className="font-medium group-hover:text-ember-glow">{t} <span className="opacity-0 transition group-hover:opacity-100">→</span></p>
                  <p className="mt-1 text-xs leading-relaxed text-ink-mute">{d}</p>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>

        {/* honesty */}
        <Reveal>
          <Head eyebrow="What the data does not cover" title="Limits, stated up front">
            {n ? `${n.skipped_files_total} files could not be indexed (scans, raw lab sheets) and some downloads failed. ` : ""}
            Some experiments keep most of their data in tables, three SAFFIRE experiments have very similar text, and the free language-model quota is limited. The About page lists every gap.
          </Head>
          <Link href="/about" className="btn-ghost mt-5 text-sm">Read the coverage notes</Link>
        </Reveal>

        {/* final CTA */}
        <Reveal>
          <div className="card relative overflow-hidden border-ember/30 p-8 text-center md:p-12">
            <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-96 -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(255,107,31,.28),transparent)]" aria-hidden />
            <h2 className="h-display relative text-3xl font-semibold md:text-4xl">Start with a scenario and a question</h2>
            <p className="relative mx-auto mt-3 max-w-xl text-sm text-ink-dim">For example: Lunar Habitat, “flame spread”. Then ask the assistant what the study establishes and what remains uncertain.</p>
            <div className="relative mt-6 flex flex-wrap justify-center gap-3">
              <Link href="/dashboard" className="btn-primary !px-6 !py-3 text-base">Enter dashboard</Link>
              <Link href="/assistant" className="btn-ghost !px-6 !py-3 text-base">Ask the assistant</Link>
            </div>
          </div>
        </Reveal>
      </div>

      <footer className="border-t border-line px-6 py-8 md:px-10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 text-xs text-ink-mute">
          <Wordmark />
          <span>Built for NASA Space Apps 2026 · Flame in Freefall</span>
          <span className="md:ml-auto">Data: NASA Physical Sciences Informatics. Not a NASA product. No certification or safety prediction.</span>
        </div>
      </footer>
    </div>
  );
}
