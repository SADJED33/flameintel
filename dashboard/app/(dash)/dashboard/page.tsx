"use client";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFetch } from "@/lib/useFetch";
import { useScenario } from "@/lib/scenario";
import InvestigationCard, { Card } from "@/components/InvestigationCard";
import { AVAIL_LABEL, EvidenceLabel, EvidenceKind, Spinner } from "@/components/Badges";
import { Button, EmptyState, ErrorState, GlassPanel, ScenarioSelect, SectionTitle, Stat } from "@/components/ui";
import Link from "next/link";

type Overview = {
  scenario: string;
  kpis: { indexed_investigations: number; with_data: number; topics_represented: number; scenario_matches: number; indexed_chunks: number; tabular_files: number };
  scenario_match_rule: string;
  charts: { topics: [string, number][]; environments: [string, number][]; availability: [string, number][] };
  featured: Card[];
  disclaimer: string;
};
type Insights = { generated_at?: string; insights: { id: string; theme: string; title: string; evidence_label: EvidenceKind; summary: string; supporting: string[] }[] } | null;

// series colours sampled from the landing artwork: mint flame clouds, violet cumulus, white
const MINT = "#b4ecce", VIOLET = "#6f44e5", WHITE = "#ffffff", MINT_DEEP = "#5a8374", VIOLET_LIGHT = "#a590f5";
const PAL = [MINT, VIOLET, WHITE, MINT_DEEP, VIOLET_LIGHT];
const AXIS = "rgba(255,255,255,.25)";
const TICK = { fill: "rgba(255,255,255,.72)", fontSize: 12 };
const TIP = { background: "rgba(18,18,20,.88)", border: "1px solid rgba(255,255,255,.15)", borderRadius: 10, fontSize: 12, color: "#fff", backdropFilter: "blur(18px) saturate(140%)", WebkitBackdropFilter: "blur(18px) saturate(140%)", boxShadow: "0 18px 44px rgba(0,0,0,.55)" } as React.CSSProperties;

const GRAVITY: Record<string, string> = {
  "Lunar Habitat": "Lunar gravity is about 1/6 g. The flight experiments here ran in microgravity, not lunar gravity.",
  "Mars Habitat": "Mars gravity is about 3/8 g. The flight experiments here ran in microgravity, not Mars gravity.",
  "Pressurized Rover": "A rover works under partial gravity or on Earth. The flight experiments here ran in microgravity.",
  ISS: "The ISS experiments match the microgravity condition, but cabin atmosphere and airflow can still differ from each test.",
  Spacecraft: "Spacecraft are in microgravity. Check that each test's atmosphere and airflow match the vehicle.",
};

export default function OverviewPage() {
  const { scenario } = useScenario();
  const { data, error, loading, reload } = useFetch<Overview>(`/api/overview?scenario=${encodeURIComponent(scenario)}`);
  const ins = useFetch<Insights>("/api/insights");

  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (loading || !data) return <Spinner label="Loading the overview…" />;
  const k = data.kpis;
  const topics = data.charts.topics.map(([name, n]) => ({ name, n }));
  const envs = data.charts.environments.map(([name, n]) => ({ name, n }));
  const avail = data.charts.availability.map(([name, n]) => ({ name: AVAIL_LABEL(name), n }));

  return (
    <div className="space-y-8">
      <SectionTitle eyebrow="Overview" title="What research and data are available?" right={<ScenarioSelect />}>
        Numbers below are computed from the imported NASA PSI records and the search index. Nothing on this page is demo data.
      </SectionTitle>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4" aria-label="Key figures">
        <Stat label="Indexed investigations" value={k.indexed_investigations} hint="NASA PSI combustion records in the knowledge base" />
        <Stat label="With data files" value={k.with_data} hint={`${k.tabular_files} tabular files (CSV / Excel) in total`} />
        <Stat label="Topics represented" value={k.topics_represented} hint="app-tagged from the record text" />
        <Stat label={`Matches · ${scenario}`} value={k.scenario_matches} hint={data.scenario_match_rule} />
      </section>

      <section className="rounded-panel border border-warm/40 bg-warm/10 px-4 py-3 text-sm text-white [-webkit-backdrop-filter:blur(10px)] [backdrop-filter:blur(10px)]">
        <span className="font-medium text-warm">Gravity note · </span>{GRAVITY[scenario]}
      </section>

      <section className="grid gap-4 lg:grid-cols-3" aria-label="Charts">
        <GlassPanel className="p-5 lg:col-span-2">
          <h2 className="text-lg">Investigations by topic</h2>
          <p className="text-xs text-ink-mute">An investigation can carry several topics.</p>
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topics} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" allowDecimals={false} tick={TICK} axisLine={{ stroke: AXIS }} tickLine={{ stroke: AXIS }} />
                <YAxis type="category" dataKey="name" width={150} tick={TICK} axisLine={{ stroke: AXIS }} tickLine={false} />
                <Tooltip contentStyle={TIP} cursor={{ fill: "rgba(255,255,255,.06)" }} />
                <Bar dataKey="n" name="Investigations" fill={MINT} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassPanel>
        <GlassPanel className="p-5">
          <h2 className="text-lg">By environment</h2>
          <div className="mt-2 h-44">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={envs} dataKey="n" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={3} stroke="none">
                  {envs.map((_, i) => <Cell key={i} fill={PAL[i % PAL.length]} />)}
                </Pie>
                <Tooltip contentStyle={TIP} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-1 space-y-1 text-xs text-ink-dim">
            {envs.map((e, i) => <li key={e.name} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: PAL[i % PAL.length] }} />{e.name}<span className="num ml-auto">{e.n}</span></li>)}
          </ul>
        </GlassPanel>
        <GlassPanel className="p-5 lg:col-span-3">
          <h2 className="text-lg">By data availability</h2>
          <div className="mt-3 h-36">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={avail} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" allowDecimals={false} tick={TICK} axisLine={{ stroke: AXIS }} tickLine={{ stroke: AXIS }} />
                <YAxis type="category" dataKey="name" width={160} tick={TICK} axisLine={{ stroke: AXIS }} tickLine={false} />
                <Tooltip contentStyle={TIP} cursor={{ fill: "rgba(255,255,255,.06)" }} />
                <Bar dataKey="n" name="Investigations" fill={VIOLET} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassPanel>
      </section>

      <section>
        <SectionTitle as="h2" title={`Featured for ${scenario}`} right={<Button href="/explorer" size="sm">Open the Explorer →</Button>}>
          Top 4 by app-generated relevance. {data.disclaimer}
        </SectionTitle>
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {data.featured.map((c) => <InvestigationCard key={c.id} c={c} scenario={scenario} compact />)}
        </div>
      </section>

      <section>
        <SectionTitle as="h2" title="Recent evidence-linked insights" right={<Button href="/insights" size="sm">All insights →</Button>} />
        <div className="mt-5">
          {ins.loading ? <Spinner label="Loading insights…" /> : !ins.data || ins.data.insights.length === 0 ? (
            <EmptyState title="Insights have not been generated yet" hint="Run python api/build_insights.py (needs the language-model key) to create them." />
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {ins.data.insights.slice(0, 3).map((i) => (
                <Link key={i.id} href="/insights" className="panel block p-5 transition-colors hover:border-white/35">
                  <EvidenceLabel kind={i.evidence_label} />
                  <p className="mt-3 font-medium leading-snug">{i.title}</p>
                  <p className="mt-1.5 line-clamp-3 text-sm text-ink-dim">{i.summary}</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
