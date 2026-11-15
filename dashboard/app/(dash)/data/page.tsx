"use client";
import { useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Spinner } from "@/components/Badges";
import { Button, DataTable, EmptyState, ErrorState, GlassPanel, Pill, SectionTitle, Tabs, type Col, type Tone } from "@/components/ui";

type DS = {
  id: string; psi: string; acronym: string; file_name: string; display_name: string; format: string; category: string;
  size_kb: number; extraction_status: string; extraction_detail: string;
};
type Col_ = { name: string; dtype: string; unit: string | null; missing: number; missing_pct: number; unique: number; examples: unknown[]; min?: number; max?: number };
type Check = { id: string; question: string; status: "pass" | "warn" | "fail"; detail: string };
type Preview = {
  dataset: DS; ok: boolean; error: string | null; sheets: string[]; sheet: string | null; rows?: number; columns_count?: number;
  truncated?: boolean; row_cap?: number; columns?: Col_[]; rows_preview?: unknown[][]; quality_notes?: string[];
  ml_readiness?: { checks: Check[]; verdict: string; message: string; note: string };
};
type List = { total: number; datasets: DS[]; facets: { formats: string[]; categories: string[]; psi: string[] }; note: string };

const ST: Record<Check["status"], { label: string; tone: Tone }> = { pass: { label: "OK", tone: "mint" }, warn: { label: "Unclear", tone: "violet" }, fail: { label: "Not met", tone: "warm" } };
const fmt = (v: unknown) => (v === null || v === undefined ? "" : String(v));

export default function DataPage() {
  const [psi, setPsi] = useState("");
  const [q, setQ] = useState("");
  const [format, setFormat] = useState("");
  const [id, setId] = useState("");
  const [sheet, setSheet] = useState("");
  const [tab, setTab] = useState("ready");

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("psi")) setPsi(p.get("psi")!);
    if (p.get("id")) { setId(p.get("id")!); setPsi(p.get("id")!.split("~")[0]); }
  }, []);

  const listUrl = useMemo(() => `/api/datasets?${new URLSearchParams({ psi, q, format })}`, [psi, q, format]);
  const list = useFetch<List>(listUrl);
  const prev = useFetch<Preview>(id ? `/api/datasets/${encodeURIComponent(id)}/preview?sheet=${encodeURIComponent(sheet)}` : null, 120000);
  const p = prev.data;

  const colCols: Col<Col_>[] = [
    { key: "name", label: "Column", className: "!text-white font-medium" },
    { key: "dtype", label: "Type", mono: true },
    { key: "unit", label: "Unit (from header)", render: (c) => c.unit ?? <span className="text-ink-mute">not documented</span> },
    { key: "missing", label: "Missing", render: (c) => <span className="num">{c.missing} <span className="text-ink-mute">({c.missing_pct}%)</span></span> },
    { key: "unique", label: "Unique", className: "num" },
    { key: "range", label: "Min / max", mono: true, render: (c) => (c.min !== undefined ? `${c.min} / ${c.max}` : "") },
    { key: "ex", label: "Examples", className: "max-w-[240px] truncate", render: (c) => c.examples.map(fmt).join(" · ") },
  ];
  const prevCols: Col<unknown[]>[] = p?.columns ? p.columns.map((c, j) => ({ key: String(j), label: c.name, mono: true, render: (r: unknown[]) => (r[j] === null ? <span className="text-ink-mute">—</span> : fmt(r[j])) })) : [];

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="Data Explorer" title="Can I use the experimental data?">
        Real CSV and Excel files from the PSI records, parsed with pandas. Columns, types and missing counts are read from the file; a unit is shown only if the file&apos;s own header states it. Nothing is predicted here.
      </SectionTitle>

      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <GlassPanel className="flex max-h-[calc(100vh-8rem)] flex-col p-3 xl:sticky xl:top-[76px]">
          <div className="space-y-2 p-1">
            <input className="input" placeholder="Filter by file name" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter files" />
            <div className="grid grid-cols-2 gap-2">
              <select className="input" value={psi} onChange={(e) => setPsi(e.target.value)} aria-label="Investigation">
                <option value="">All investigations</option>
                {list.data?.facets.psi.map((x) => <option key={x}>{x}</option>)}
              </select>
              <select className="input" value={format} onChange={(e) => setFormat(e.target.value)} aria-label="Format">
                <option value="">All formats</option>
                {list.data?.facets.formats.map((x) => <option key={x} value={x}>{x.toUpperCase()}</option>)}
              </select>
            </div>
            <p className="text-xs text-ink-mute">{list.data ? `${list.data.total} files` : ""}</p>
          </div>
          <div className="min-h-0 max-h-[50vh] flex-1 overflow-y-auto xl:max-h-none">
            {list.loading && <Spinner label="Loading files…" />}
            {list.error && <ErrorState message={list.error.message} onRetry={list.reload} />}
            {list.data?.total === 0 && <p className="p-3 text-sm text-ink-dim">No file matches.</p>}
            <ul className="space-y-0.5">
              {list.data?.datasets.map((d) => (
                <li key={d.id}>
                  <button onClick={() => { setId(d.id); setSheet(""); }} aria-current={id === d.id}
                    className={`w-full rounded-btn px-2.5 py-2 text-left transition-colors ${id === d.id ? "bg-white/[.14] shadow-[inset_2px_0_0_#b4ecce]" : "hover:bg-white/[.07]"}`}>
                    <div className="flex items-center gap-2">
                      <span className="pill !px-2 !py-0.5 !text-[10px] uppercase">{d.format}</span>
                      <span className="num text-[11px] font-medium text-mint">{d.psi}</span>
                      <span className="num ml-auto text-[10px] text-ink-mute">{d.size_kb >= 1024 ? `${(d.size_kb / 1024).toFixed(1)} MB` : `${d.size_kb} KB`}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-ink-dim">{d.display_name}</p>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </GlassPanel>

        <section className="min-w-0 space-y-5">
          {!id && <EmptyState title="Pick a file to inspect" hint={list.data?.note || "Choose a dataset on the left."} />}
          {id && prev.loading && <Spinner label="Parsing the file… large Excel files can take up to a minute the first time (then they are cached)." />}
          {id && prev.error && <ErrorState message={prev.error.message} onRetry={prev.reload} />}
          {p && !p.ok && <ErrorState message={p.error || "This file could not be previewed."} />}

          {p && (
            <>
              <GlassPanel className="p-5">
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="num text-xs font-medium text-mint">{p.dataset.psi}{p.dataset.acronym ? ` · ${p.dataset.acronym}` : ""} · {p.dataset.category}</p>
                    <h2 className="mt-1 break-words text-lg">{p.dataset.display_name}</h2>
                    <p className="mt-1.5 text-xs text-ink-mute">Extraction status: <span className="text-white">{p.dataset.extraction_status}</span> — {p.dataset.extraction_detail}</p>
                  </div>
                  {p.ok && <Button variant="solid" href={`${API}/api/datasets/${encodeURIComponent(p.dataset.id)}/export?sheet=${encodeURIComponent(p.sheet && p.sheets.length ? p.sheet : "")}`} external>Export CSV</Button>}
                </div>
                {p.sheets.length > 1 && (
                  <label className="mt-3 block text-xs text-ink-mute">Sheet ({p.sheets.length})
                    <select className="input mt-1 max-w-md" value={p.sheet || ""} onChange={(e) => setSheet(e.target.value)}>{p.sheets.map((s) => <option key={s}>{s}</option>)}</select>
                  </label>
                )}
                {p.ok && (
                  <div className="mt-4 flex flex-wrap gap-x-7 gap-y-1 text-sm">
                    <span><b className="num text-base">{p.rows?.toLocaleString("en-US")}</b> <span className="text-ink-mute">rows{p.truncated ? ` (first ${p.row_cap?.toLocaleString("en-US")} scanned)` : ""}</span></span>
                    <span><b className="num text-base">{p.columns_count}</b> <span className="text-ink-mute">columns</span></span>
                    <span><b className="num text-base">{p.columns?.filter((c) => c.unit).length}</b> <span className="text-ink-mute">with a documented unit</span></span>
                  </div>
                )}
                {p.quality_notes && p.quality_notes.length > 0 && (
                  <ul className="mt-4 space-y-1 rounded-btn border border-warm/40 bg-warm/10 p-3 text-xs text-ink-dim">
                    <li className="font-medium text-warm">Quality notes</li>
                    {p.quality_notes.map((n, i) => <li key={i}>{n}</li>)}
                  </ul>
                )}
              </GlassPanel>

              {p.ok && (
                <>
                  <Tabs label="Dataset views" value={tab} onChange={setTab} tabs={[{ id: "ready", label: "ML-readiness" }, { id: "columns", label: "Columns and missing values" }, { id: "preview", label: "Preview" }]} />
                  {tab === "ready" && p.ml_readiness && (
                    <GlassPanel className={`p-5 sm:p-6 ${p.ml_readiness.verdict === "not_ready" ? "!border-warm/40" : ""}`}>
                      <h3 className="text-xl">ML-readiness checklist</h3>
                      <p className={`mt-1.5 text-sm font-medium ${p.ml_readiness.verdict === "not_ready" ? "text-warm" : "text-violet-ink"}`}>{p.ml_readiness.message}</p>
                      <ul className="mt-4 divide-y divide-white/10 rounded-btn border border-white/15">
                        {p.ml_readiness.checks.map((c) => (
                          <li key={c.id} className="flex items-start gap-3 px-3 py-3 text-sm">
                            <span className="mt-0.5 shrink-0"><Pill tone={ST[c.status].tone}>{ST[c.status].label}</Pill></span>
                            <div><p>{c.question}</p><p className="text-xs text-ink-mute">{c.detail}</p></div>
                          </li>
                        ))}
                      </ul>
                      <p className="mt-3 text-[11px] text-ink-mute">{p.ml_readiness.note}</p>
                    </GlassPanel>
                  )}
                  {tab === "columns" && p.columns && <DataTable columns={colCols} rows={p.columns} caption="Columns, types and missing values" rowKey={(c) => c.name} />}
                  {tab === "preview" && p.columns && p.rows_preview && (
                    <div className="space-y-2">
                      <p className="text-xs text-ink-mute">First {p.rows_preview.length} rows, exactly as parsed from the file.</p>
                      <DataTable columns={prevCols} rows={p.rows_preview} caption="Preview of the first rows" maxHeight={480} />
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
