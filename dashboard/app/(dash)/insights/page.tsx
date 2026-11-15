"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useFetch } from "@/lib/useFetch";
import { EvidenceLabel, Spinner } from "@/components/Badges";
import { Button, Drawer, EmptyState, ErrorState, GlassPanel, SectionTitle, Tabs } from "@/components/ui";

type Cite = { id: string; psi: string; acronym: string; doc_type: string; file: string; loc: string; distance: number; excerpt: string };
type Claim = { text: string; kind: string; citations: Cite[] };
type Insight = {
  id: string; theme: string; title: string; outcome: string; claims: Claim[]; supporting: string[];
  app_interpretation: { text: string }; potential_application: { text: string }; limitations: string[]; validation_required: string;
  warnings: { issue: string; numbers: string[]; text: string }[];
};
type Res = { generated_at: string | null; method?: string; insights: Insight[]; note?: string };

export default function InsightsPage() {
  const { data, error, loading, reload } = useFetch<Res>("/api/insights");
  const [theme, setTheme] = useState("all");
  const [cite, setCite] = useState<Cite | null>(null);
  const themes = useMemo(() => Array.from(new Set(data?.insights.map((i) => i.theme) ?? [])), [data]);
  const shown = data?.insights.filter((i) => theme === "all" || i.theme === theme) ?? [];

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="Fire Safety Insights" title="What fire-safety themes might this research inform?">
        Each card starts from sentences the assistant could cite from NASA PSI sources. FlameIntel&apos;s own reading and the possible applications are labelled separately and never presented as NASA findings or certification.
        {data?.generated_at && <> Generated offline on {data.generated_at.replace("T", " ")} from {data.insights.length} fixed questions.</>}
      </SectionTitle>

      {loading && <Spinner label="Loading insights…" />}
      {error && <ErrorState message={error.message} onRetry={reload} />}
      {data && data.insights.length === 0 && <EmptyState title="No insights generated yet" hint="Run python api/build_insights.py (needs the language-model key)." />}

      {themes.length > 0 && <Tabs label="Theme" value={theme} onChange={setTheme} tabs={[{ id: "all", label: "All themes" }, ...themes.map((t) => ({ id: t, label: t }))]} />}

      <div className="grid gap-5 xl:grid-cols-2">
        {shown.map((i) => (
          <GlassPanel key={i.id} className="space-y-4 p-5 sm:p-6">
            <div>
              <p className="eyebrow">{i.theme}</p>
              <h2 className="mt-1.5 text-xl leading-snug">{i.title}?</h2>
              {i.outcome === "partial" && <p className="mt-1.5 text-xs text-violet-ink">Partial: the sources do not cover every part of this question.</p>}
            </div>

            <div>
              <EvidenceLabel kind="source_reported" />
              <ul className="mt-3 space-y-2.5 text-sm">
                {i.claims.slice(0, 4).map((c, k) => (
                  <li key={k} className="flex gap-2.5">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-mint" />
                    <span className="text-white">{c.text}{" "}
                      {c.citations.map((ct) => (
                        <button key={ct.id} onClick={() => setCite(ct)} title={`${ct.psi} · ${ct.doc_type}`}
                          className="mx-0.5 rounded-full border border-mint/50 bg-mint/10 px-2 text-[11px] font-medium text-mint transition-colors hover:bg-mint hover:text-black">{ct.psi.replace("PSI-", "P")}·{ct.id}</button>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
              {i.claims.length > 4 && <p className="mt-2 text-xs text-ink-mute">+ {i.claims.length - 4} more cited statements in the report.</p>}
            </div>

            <div><EvidenceLabel kind="app_interpretation" /><p className="mt-2 text-sm text-ink-dim">{i.app_interpretation.text}</p></div>
            <div><EvidenceLabel kind="potential_application" /><p className="mt-2 text-sm text-ink-dim">{i.potential_application.text}</p></div>

            <div className="flex flex-wrap items-center gap-1.5">
              <span className="eyebrow mr-1">Supporting</span>
              {i.supporting.map((p) => <Link key={p} href={`/investigations/${p}`} className="chip">{p}</Link>)}
            </div>

            {i.warnings.length > 0 && <p className="rounded-btn border border-warm/50 bg-warm/10 px-3 py-2 text-xs text-warm">Number check flagged {i.warnings.length} statement(s) in the original answer; verify figures in the source.</p>}

            <details className="text-xs text-ink-mute">
              <summary className="cursor-pointer text-ink-dim transition-colors hover:text-white">Limitations and validation required</summary>
              <ul className="mt-2 list-disc space-y-1 pl-5">{i.limitations.map((l, k) => <li key={k}>{l}</li>)}</ul>
              <p className="mt-2 rounded-btn border border-white/15 bg-white/[.06] p-2.5 text-ink-dim"><b className="text-warm">Validation required. </b>{i.validation_required}</p>
            </details>
          </GlassPanel>
        ))}
      </div>

      <Drawer open={!!cite} onClose={() => setCite(null)} label="Citation">
        {cite && (
          <>
            <div className="flex items-start gap-3 border-b border-white/15 p-4">
              <div className="min-w-0 flex-1">
                <p className="font-medium">{cite.psi}{cite.acronym ? ` · ${cite.acronym}` : ""}</p>
                <p className="mt-1 break-all font-mono text-[11px] text-ink-mute">{cite.doc_type} · {cite.file} · {cite.loc} · distance {cite.distance}</p>
              </div>
              <Button size="sm" onClick={() => setCite(null)} autoFocus>Close</Button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              <p className="eyebrow mb-2">Excerpt</p>
              <pre className="whitespace-pre-wrap break-words font-mono text-[12px] leading-relaxed text-ink-dim">{cite.excerpt}{cite.excerpt.length >= 500 ? "…" : ""}</pre>
            </div>
            <div className="border-t border-white/15 p-3"><Button href={`/investigations/${cite.psi}`} size="sm" className="w-full">Open {cite.psi}</Button></div>
          </>
        )}
      </Drawer>
    </div>
  );
}
