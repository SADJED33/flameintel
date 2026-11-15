"use client";
import { useEffect, useState } from "react";
import { useFetch } from "@/lib/useFetch";
import { useScenario } from "@/lib/scenario";
import { Spinner } from "@/components/Badges";
import { DataTable, EmptyState, ErrorState, GlassPanel, ScenarioSelect, SectionTitle, type Col } from "@/components/ui";

type Inv = { id: string; acronym: string; title: string; name: string };
type Row = { label: string; values: string[]; note: string };
type Cmp = {
  investigations: { id: string; name: string; title: string; source_url: string }[];
  rows: Row[]; mismatches: string[]; numeric_comparison_allowed: boolean; numeric_comparison_note: string;
};

export default function ComparePage() {
  const { scenario } = useScenario();
  const [ids, setIds] = useState<string[]>([]);
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("ids");
    if (p) setIds(p.split(",").filter(Boolean).slice(0, 3));
  }, []);
  const all = useFetch<{ items: Inv[] }>("/api/investigations");
  const cmp = useFetch<Cmp>(ids.length >= 2 ? `/api/compare?ids=${ids.join(",")}&scenario=${encodeURIComponent(scenario)}` : null);
  const toggle = (id: string) => setIds((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 3 ? s : [...s, id]));

  const cols: Col<Row>[] = cmp.data ? [
    { key: "label", label: "", className: "w-56 !text-white font-medium", render: (r) => <>{r.label}{r.note && <span className="mt-1 block text-[11px] font-normal text-ink-mute">{r.note}</span>}</> },
    ...cmp.data.investigations.map((i, k) => ({ key: i.id, label: `${i.id} · ${i.name}`, className: "min-w-[260px] text-[13px] leading-relaxed", render: (r: Row) => r.values[k] })),
  ] : [];

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="Investigation Comparison" title="Where do two or three studies agree, and where not?" right={<ScenarioSelect />}>
        A qualitative comparison. Numbers are never lined up as equivalent unless units, definitions and conditions match; otherwise the page explains the mismatch.
      </SectionTitle>

      <GlassPanel className="p-4">
        <p className="eyebrow mb-3">Choose 2 or 3 ({ids.length} selected)</p>
        {all.loading && <Spinner label="Loading…" />}
        {all.error && <ErrorState message={all.error.message} onRetry={all.reload} />}
        <div className="flex flex-wrap gap-2">
          {all.data?.items.map((i) => (
            <button key={i.id} onClick={() => toggle(i.id)} aria-pressed={ids.includes(i.id)} title={i.title}
              className={`chip ${ids.includes(i.id) ? "!border-mint !bg-mint !text-black" : ""}`}>{i.id} · {i.name}</button>
          ))}
        </div>
      </GlassPanel>

      {ids.length < 2 && <EmptyState title="Select at least two investigations" hint="You can also tick “Compare” on cards in the Explorer." />}
      {cmp.loading && ids.length >= 2 && <Spinner label="Comparing…" />}
      {cmp.error && <ErrorState message={cmp.error.message} onRetry={cmp.reload} />}

      {cmp.data && (
        <>
          <div className={`rounded-panel border px-4 py-3 text-sm ${cmp.data.numeric_comparison_allowed ? "border-mint/50 bg-mint/10 text-white" : "border-warm/50 bg-warm/10 text-white"}`}>
            <b className={cmp.data.numeric_comparison_allowed ? "text-mint" : "text-warm"}>{cmp.data.numeric_comparison_allowed ? "Numeric comparison possible, with care. " : "Qualitative comparison only. "}</b>{cmp.data.numeric_comparison_note}
          </div>
          <DataTable columns={cols} rows={cmp.data.rows} caption="Comparison of the selected investigations" maxHeight={640} rowKey={(r) => r.label} />
          <GlassPanel className="p-5 sm:p-6">
            <h2 className="text-xl">Why these studies are not like-for-like</h2>
            <ul className="mt-3 space-y-2.5 text-sm text-ink-dim">
              {cmp.data.mismatches.map((m, i) => <li key={i} className="flex gap-2.5"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-warm" />{m}</li>)}
            </ul>
          </GlassPanel>
        </>
      )}
    </div>
  );
}
