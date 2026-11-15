"use client";
import { useFetch } from "@/lib/useFetch";
import { Spinner } from "@/components/Badges";
import { ErrorState, GlassPanel, SectionTitle, Stat } from "@/components/ui";

type Cov = {
  investigations: number; indexed_chunks: number; skipped_files_total: number; skipped_raw_lab_sheet_or_plot: number;
  pdf_no_extractable_text_or_error: number; failed_downloads: number; failed_download_files: { psi: string; file: string; problem: string }[];
  excel_sheets_skipped: number; excluded_rocket_propellant: string[]; built_at: string;
};

export default function AboutPage() {
  const { data, error, loading, reload } = useFetch<{ coverage: Cov }>("/api/coverage");
  const c = data?.coverage;
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <SectionTitle eyebrow="About the data" title="What is covered, and what is not">
        FlameIntel works from 24 NASA Physical Sciences Informatics (PSI) microgravity combustion investigations. Honest limits first.
      </SectionTitle>
      {loading && <Spinner label="Loading coverage…" />}
      {error && <ErrorState message={error.message} onRetry={reload} />}
      {c && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Investigations" value={c.investigations} />
            <Stat label="Indexed passages" value={c.indexed_chunks.toLocaleString("en-US")} />
            <Stat label="Files skipped" value={c.skipped_files_total} />
            <Stat label="Failed downloads" value={c.failed_downloads} />
          </div>
          <GlassPanel className="space-y-3 p-5 sm:p-6 text-sm leading-relaxed text-ink-dim">
            <h2 className="text-xl text-white">Coverage notes</h2>
            <ul className="list-disc space-y-2.5 pl-5">
              <li><b className="font-medium text-white">{c.skipped_files_total} files were skipped</b> when building the search index: {c.skipped_raw_lab_sheet_or_plot} raw lab sheets or plots and {c.pdf_no_extractable_text_or_error} PDFs with no extractable text (scans or images). Their content is not searchable by the assistant.</li>
              <li><b className="font-medium text-white">{c.failed_downloads} downloads failed</b> (listed below), so those documents are missing.</li>
              <li><b className="font-medium text-white">{c.excel_sheets_skipped} Excel sheets</b> were skipped because they were empty or had no header row.</li>
              <li><b className="font-medium text-white">FLEX (PSI-69), FLEX-2 (PSI-68) and PSI-20</b> keep most of their data in tables and spreadsheets, so the text index describes them less deeply than the PDF-heavy experiments.</li>
              <li><b className="font-medium text-white">SAFFIRE-I, II and III</b> have very similar text. Check the experiment id on every citation before relying on a passage.</li>
              <li><b className="font-medium text-white">The free language-model quota is limited.</b> Under heavy use the assistant may be slow, switch to a backup model (shown on the answer), or ask you to try again later.</li>
              <li>Rocket and propellant research is excluded{c.excluded_rocket_propellant.length ? ` (${c.excluded_rocket_propellant.join(", ")})` : " (none of the 24 records matched)"}.</li>
              <li>Topic tags and relevance scores are app-generated from the record text and a documented heuristic. They are not official NASA classifications or scores.</li>
            </ul>
          </GlassPanel>
          <GlassPanel className="p-5 sm:p-6">
            <h2 className="text-xl">Files that could not be downloaded</h2>
            <ul className="mt-3 divide-y divide-white/10 text-xs">
              {c.failed_download_files.map((f, i) => (
                <li key={i} className="flex flex-wrap gap-x-3 gap-y-1 py-2.5"><span className="num font-medium text-mint">{f.psi}</span><span className="break-all text-ink-dim">{f.file}</span><span className="text-warm sm:ml-auto">{f.problem}</span></li>
              ))}
            </ul>
          </GlassPanel>
          <p className="text-xs text-ink-mute">Counts are computed from the build files, last built {c.built_at.replace("T", " ")}. FlameIntel organizes existing research; it does not run experiments, replace NASA sources or certify equipment.</p>
        </>
      )}
    </div>
  );
}
