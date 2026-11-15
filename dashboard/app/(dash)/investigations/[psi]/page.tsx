"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useFetch } from "@/lib/useFetch";
import { useScenario } from "@/lib/scenario";
import type { Investigation } from "@/lib/types";
import { AvailabilityBadge, EvidenceLabel, Spinner } from "@/components/Badges";
import RankGauge from "@/components/RankGauge";
import { Button, ErrorState, GlassPanel, ScenarioSelect, Tabs, Tag, Tooltip } from "@/components/ui";

type Detail = Investigation & {
  evidence: {
    source_reported: { label: string; text: string; citation: string; url: string }[];
    app_interpretation: string[];
    potential_application: { topic: string; text: string }[];
    potential_application_note: string;
  };
  measured_variables_note: string;
};
type DS = { datasets: { id: string; file_name: string; format: string; size_kb: number; extraction_status: string; sheets: number | null }[] };

const unitOf = (c: string) => c.match(/\(([^)]+)\)\s*$/)?.[1] ?? null;

function Section({ title, kind, children }: { title: string; kind?: "source_reported" | "app_interpretation" | "potential_application"; children: React.ReactNode }) {
  return (
    <GlassPanel className="min-w-0 p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="text-xl">{title}</h2>
        {kind && <EvidenceLabel kind={kind} />}
      </div>
      {children}
    </GlassPanel>
  );
}

export default function DetailPage() {
  const { psi } = useParams<{ psi: string }>();
  const { scenario } = useScenario();
  const { data: d, error, loading, reload } = useFetch<Detail>(`/api/investigations/${psi}?scenario=${encodeURIComponent(scenario)}`);
  const ds = useFetch<DS>(`/api/datasets?psi=${psi}`);
  const [tab, setTab] = useState("");

  if (error) return <ErrorState message={error.type === "http" ? `No investigation called ${psi}.` : error.message} onRetry={reload} />;
  if (loading || !d) return <Spinner label="Loading the investigation…" />;
  const ask = `/assistant?q=${encodeURIComponent(`What results did ${d.acronym || d.title} report, and what remains uncertain?`)}`;
  const sr = d.evidence.source_reported;
  const active = sr.find((s) => s.label === tab) || sr[0];

  return (
    <div className="space-y-5">
      <Link href="/explorer" className="text-xs text-ink-mute transition-colors hover:text-white">← Explorer</Link>
      <header className="flex flex-wrap items-start gap-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="num text-sm font-medium text-mint">{d.id}</span>
            <AvailabilityBadge value={d.availability} />
          </div>
          <h1 className="mt-2 text-[clamp(2rem,4vw,3rem)]">{d.acronym || d.title}</h1>
          {d.acronym && <p className="mt-1 text-ink-dim">{d.title}</p>}
          <div className="mt-5 flex flex-wrap gap-2">
            <Button href={d.source_url} external variant="solid">Original PSI record ↗</Button>
            <Button href={ask}>Ask the assistant about this study</Button>
            <Button href={`/data?psi=${d.id}`}>Inspect its data</Button>
          </div>
          <p className="mt-2 text-[11px] text-ink-mute">{d.source_url_note}.</p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <ScenarioSelect />
          {d.rank && (
            <GlassPanel className="flex items-center gap-4 p-4">
              <RankGauge score={d.rank.score} size={72} />
              <p className="max-w-[230px] text-xs text-ink-mute">Relevance for <span className="text-white">{scenario}</span>. App-generated, not an official NASA score.</p>
            </GlassPanel>
          )}
        </div>
      </header>

      <div className="flex flex-wrap gap-1.5">{d.topics.map((t) => <Tag key={t}>{t}</Tag>)}</div>

      <Section title="Research objective and description" kind="source_reported">
        {sr.length === 0 ? <p className="text-sm text-ink-dim">The record has no objective or description text.</p> : (
          <div className="space-y-4">
            <Tabs label="Record text" tabs={sr.map((s) => ({ id: s.label, label: s.label }))} value={active.label} onChange={setTab} />
            <div>
              <p className="whitespace-pre-line text-[15px] leading-relaxed text-white [font-variation-settings:'opsz'_20]">{active.text}</p>
              <p className="mt-2 text-[11px] text-ink-mute">Source: <a className="underline underline-offset-2 hover:text-mint" href={active.url} target="_blank" rel="noreferrer">{active.citation}</a></p>
            </div>
          </div>
        )}
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="Platform and environment" kind="source_reported">
          <dl className="grid grid-cols-[130px_1fr] gap-y-2.5 text-sm">
            <dt className="text-ink-mute">Platform</dt><dd>{d.environment}{d.flight_program ? ` · ${d.flight_program}` : ""}</dd>
            <dt className="text-ink-mute">Record type</dt><dd>{d.project_type || "not stated"}</dd>
            <dt className="text-ink-mute">Gravity</dt><dd>{d.gravity_condition} <span className="text-[11px] text-ink-mute">(from the record type)</span></dd>
            <dt className="text-ink-mute">Dates</dt><dd>{d.start_date || "?"} to {d.end_date || "?"}</dd>
            <dt className="text-ink-mute">NASA center</dt><dd>{d.managing_center || "not stated"}</dd>
            <dt className="text-ink-mute">Principal investigator</dt><dd>{d.principal_investigator || "not stated"}</dd>
            <dt className="text-ink-mute">Record updated</dt><dd>{d.source_updated_at || "not stated"}</dd>
            <dt className="text-ink-mute">License</dt><dd>{d.license || "not stated"}</dd>
          </dl>
        </Section>

        <Section title="Materials, conditions and variables" kind="source_reported">
          <p className="eyebrow">Materials / fuels in the experimental table</p>
          <p className="mt-1.5 text-sm text-ink-dim">{d.materials.length ? d.materials.join(" · ") : "No materials column found in an experimental table."}</p>
          <p className="eyebrow mt-5">Table columns (units only if in the header)</p>
          {d.condition_columns.length ? (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {d.condition_columns.map((c) => (
                <li key={c}>
                  <Tooltip text={unitOf(c) ? `Unit stated in the header: ${unitOf(c)}` : "No unit in the header"}>
                    <span className="pill !py-1 !text-[11.5px]">{c}{!unitOf(c) && <span className="text-ink-mute">· no unit</span>}</span>
                  </Tooltip>
                </li>
              ))}
            </ul>
          ) : <p className="mt-1.5 text-sm text-ink-dim">No experimental-table columns for this record.</p>}
          <p className="mt-3 text-[11px] text-ink-mute">{d.measured_variables_note}</p>
        </Section>
      </div>

      <Section title="Source-reported findings" kind="source_reported">
        <p className="text-sm leading-relaxed text-ink-dim">
          The PSI record metadata describes objectives, approach and hypothesis. Results live in the reports, papers and data files. FlameIntel does not summarise results on this page without a citation:
          ask the assistant and every statement comes back with an <span className="rounded-full border border-mint/50 bg-mint/10 px-2 text-[12px] font-medium text-mint">S#</span> source.
        </p>
        <Button href={ask} size="sm" className="mt-4">Ask: what did {d.acronym || d.id} report?</Button>
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="Data files">
          <p className="text-sm text-ink-dim">{d.tabular_file_count} tabular file(s) downloaded. File counts: {Object.entries(d.file_counts).map(([k, v]) => `${v} ${k || "other"}`).join(", ") || "none"}.</p>
          {ds.loading ? <Spinner label="Loading files…" /> : ds.error ? <p className="mt-2 text-sm text-ink-mute">The data list is unavailable right now.</p> : (
            <ul className="mt-3 max-h-64 space-y-1 overflow-y-auto pr-1 text-xs">
              {ds.data?.datasets.slice(0, 40).map((f) => (
                <li key={f.id}>
                  <Link href={`/data?id=${f.id}`} className="flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-white/[.08]">
                    <span className="pill !px-2 !py-0.5 !text-[10px] uppercase">{f.format}</span>
                    <span className="truncate">{f.file_name.replace(/^PSI-\d+_/, "")}</span>
                    <span className="ml-auto shrink-0 text-ink-mute">{f.extraction_status}</span>
                  </Link>
                </li>
              ))}
              {ds.data && ds.data.datasets.length === 0 && <li className="text-ink-mute">No tabular files for this record.</li>}
              {ds.data && ds.data.datasets.length > 40 && <li className="px-2 py-1 text-ink-mute">…and {ds.data.datasets.length - 40} more in the Data Explorer.</li>}
            </ul>
          )}
        </Section>
        <Section title="Publications">
          {d.publications.length === 0 ? <p className="text-sm text-ink-dim">No publications are listed in the record.</p> : (
            <ul className="max-h-64 space-y-3 overflow-y-auto pr-1 text-sm">
              {d.publications.map((p, i) => (
                <li key={i}>
                  {p.doi ? <a className="transition-colors hover:text-mint" href={`https://doi.org/${p.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, "")}`} target="_blank" rel="noreferrer">{p.title} ↗</a> : p.title}
                  <span className="block text-[11px] text-ink-mute">{p.authors}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Extraction notes and limitations">
        <ul className="space-y-2 text-sm text-ink-dim">
          {d.limitations.map((l, i) => <li key={i} className="flex gap-2.5"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-warm" />{l}</li>)}
          <li className="flex gap-2.5"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-warm" />{d.index_chunk_total.toLocaleString("en-US")} passages are indexed for the assistant ({Object.entries(d.index_chunks).map(([k, v]) => `${v} ${k}`).join(", ")}).</li>
        </ul>
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="Potential fire-safety relevance" kind="app_interpretation">
          <ul className="space-y-2.5 text-sm text-ink-dim">
            {d.evidence.app_interpretation.map((t, i) => <li key={i} className="flex gap-2.5"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-violet-ink" />{t}</li>)}
          </ul>
        </Section>
        <Section title="Potential application" kind="potential_application">
          {d.evidence.potential_application.length === 0 ? <p className="text-sm text-ink-dim">No application theme is tagged for this record.</p> : (
            <ul className="space-y-2.5 text-sm text-ink-dim">
              {d.evidence.potential_application.map((a) => <li key={a.topic}><span className="text-white">{a.topic}: </span>{a.text}</li>)}
            </ul>
          )}
          <p className="mt-4 rounded-btn border border-warm/40 bg-warm/10 px-3 py-2 text-xs text-warm">{d.evidence.potential_application_note} Validation required.</p>
        </Section>
      </div>
    </div>
  );
}
