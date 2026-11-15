"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useFetch } from "@/lib/useFetch";
import { useScenario } from "@/lib/scenario";
import InvestigationCard, { Card } from "@/components/InvestigationCard";
import { AVAIL_LABEL, Spinner } from "@/components/Badges";
import { Button, EmptyState, ErrorState, GlassPanel, ScenarioSelect, SearchInput, SectionTitle } from "@/components/ui";

type Res = {
  total: number; items: Card[]; disclaimer: string;
  facets: { topics: [string, number][]; environments: [string, number][]; availability: [string, number][] };
};
const EXAMPLES = ["Flame spread in reduced gravity", "Combustion data for suppression", "Flammability of materials", "Smoke detection", "Cool flames"];

export default function ExplorerPage() {
  const { scenario } = useScenario();
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [topic, setTopic] = useState("");
  const [env, setEnv] = useState("");
  const [avail, setAvail] = useState("");
  const [sel, setSel] = useState<string[]>([]);

  useEffect(() => { const t = setTimeout(() => setDq(q), 300); return () => clearTimeout(t); }, [q]);
  const url = useMemo(() => `/api/investigations?${new URLSearchParams({ q: dq, topic, environment: env, availability: avail, scenario })}`, [dq, topic, env, avail, scenario]);
  const { data, error, loading, reload } = useFetch<Res>(url);
  const toggle = (id: string) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 3 ? s : [...s, id]));
  const clear = () => { setQ(""); setTopic(""); setEnv(""); setAvail(""); };
  const filtered = q || topic || env || avail;

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="Investigation Explorer" title="Which investigations should I inspect?" right={<ScenarioSelect />}>
        Search and filter the NASA PSI records. Results are ranked for <b className="font-medium text-white">{scenario}</b> with an app-generated score, not an official NASA rating.
        Open “Why relevant?” on any card to see the reasons and the gravity caveat.
      </SectionTitle>

      <GlassPanel className="space-y-3 p-4">
        <SearchInput label="Search investigations" value={q} onChange={setQ} placeholder="Search, e.g. “flame spread in reduced gravity”" />
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="eyebrow mr-1">Try</span>
          {EXAMPLES.map((e) => <button key={e} onClick={() => setQ(e)} className="chip">{e}</button>)}
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-xs text-ink-mute">Topic
            <select className="input mt-1" value={topic} onChange={(e) => setTopic(e.target.value)}>
              <option value="">All topics</option>
              {data?.facets.topics.map(([t, n]) => <option key={t} value={t}>{t} ({n})</option>)}
            </select>
          </label>
          <label className="text-xs text-ink-mute">Environment / platform
            <select className="input mt-1" value={env} onChange={(e) => setEnv(e.target.value)}>
              <option value="">All environments</option>
              {data?.facets.environments.map(([t, n]) => <option key={t} value={t}>{t} ({n})</option>)}
            </select>
          </label>
          <label className="text-xs text-ink-mute">Data availability
            <select className="input mt-1" value={avail} onChange={(e) => setAvail(e.target.value)}>
              <option value="">Any</option>
              <option value="has_data">Has a dataset (any)</option>
              {data?.facets.availability.map(([t, n]) => <option key={t} value={t}>{AVAIL_LABEL(t)} ({n})</option>)}
            </select>
          </label>
        </div>
        <p className="text-[11px] text-ink-mute">Experimental-condition filters are not offered: they need reliable per-file condition data, which the records do not provide consistently.</p>
      </GlassPanel>

      <div className="flex flex-wrap items-center gap-3 text-sm text-ink-dim" aria-live="polite">
        {data && <span><b className="num text-white">{data.total}</b> investigation{data.total === 1 ? "" : "s"}</span>}
        {filtered && <button onClick={clear} className="text-mint underline-offset-2 hover:underline">Clear filters</button>}
        <span className="text-xs text-ink-mute md:ml-auto">{data?.disclaimer}</span>
      </div>

      {error && <ErrorState message={error.message} onRetry={reload} />}
      {loading && !data && <Spinner label="Searching…" />}
      {data && data.items.length === 0 && <EmptyState title="No investigation matches" hint="Try fewer words or clear a filter. Only the 24 indexed PSI records are searched." />}
      <div className={`grid gap-4 xl:grid-cols-2 ${loading && data ? "opacity-60 transition-opacity" : ""}`}>
        {data?.items.map((c) => <InvestigationCard key={c.id} c={c} scenario={scenario} selected={sel.includes(c.id)} onToggle={() => toggle(c.id)} />)}
      </div>

      {sel.length > 0 && (
        <div className="pop no-print fixed bottom-5 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 !rounded-full px-5 py-2.5">
          <span className="text-sm">{sel.length} selected <span className="text-ink-mute">(2 to 3)</span></span>
          <Button href={`/compare?ids=${sel.join(",")}`} variant="solid" size="sm" aria-disabled={sel.length < 2} className={sel.length < 2 ? "pointer-events-none opacity-40" : ""}>Compare</Button>
          <button onClick={() => setSel([])} className="text-xs text-ink-mute transition-colors hover:text-white">Clear</button>
        </div>
      )}
      <p className="text-xs text-ink-mute">Want a side-by-side view? Tick “Compare” on two or three cards, or <Link href="/compare" className="text-mint hover:underline">open the comparison page</Link>.</p>
    </div>
  );
}
