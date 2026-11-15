"use client";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { useScenario } from "@/lib/scenario";
import { Spinner } from "@/components/Badges";
import { Button, ErrorState, GlassPanel, ScenarioSelect, SectionTitle } from "@/components/ui";

// The API returns a white, printable document (kept as is). For the on-screen preview we only restyle it with the dashboard tokens.
const origin = () => (typeof window === "undefined" ? "" : window.location.origin);
const darkCss = () => `<style>
@font-face{font-family:"InterVar";font-weight:100 900;src:url(${origin()}/landing/assets/fonts/inter-var.woff2) format("woff2")}
:root{color-scheme:dark}
html,body{background:transparent!important;color:rgba(255,255,255,.88)!important}
body{font-family:"InterVar","Inter",Arial,system-ui,sans-serif!important;font-weight:450;max-width:860px;margin:0 auto!important;padding:8px 20px 32px!important;line-height:1.6}
h1,h2,h3{font-family:inherit!important;color:#fff;font-weight:545;letter-spacing:-.02em}
h1{border-bottom:1px solid rgba(255,255,255,.25)!important}
a{color:#b4ecce}small,.card small{color:rgba(255,255,255,.72)!important}
.card{border-color:rgba(255,255,255,.15)!important;background:rgba(255,255,255,.05);border-radius:14px!important}
.note{background:rgba(255,178,122,.10)!important;border-color:rgba(255,178,122,.45)!important;color:#fff;border-radius:10px}
table{color:rgba(255,255,255,.88)}td,th{border-color:rgba(255,255,255,.15)!important}
.tag{border-radius:999px!important;color:#fff!important;background:rgba(255,255,255,.10)!important;border-color:rgba(255,255,255,.25)!important}
.tag.sr{border-color:#b4ecce!important}.tag.ai{border-color:#6f44e5!important}.tag.pa{border-color:#fff!important}
button{display:none}
</style>`;

export default function ReportPage() {
  const { scenario } = useScenario();
  const q = `scenario=${encodeURIComponent(scenario)}`;
  const [html, setHtml] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const [n, setN] = useState(0);

  useEffect(() => {
    let live = true;
    setHtml(null); setErr("");
    fetch(`${API}/api/report?${q}`)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`Report request failed (${r.status})`))))
      .then((t) => live && setHtml(t.replace("</head>", darkCss() + "</head>")))
      .catch((e) => live && setErr(e instanceof TypeError ? `Cannot reach the FlameIntel API at ${API}.` : String(e.message)));
    return () => { live = false; };
  }, [q, n]);

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="Report export" title={`Cited report for ${scenario}`} right={<ScenarioSelect />}>
        Includes the ranked investigations with reasons, source summaries, data availability, a qualitative comparison, the fire-safety insights, citations, evidence labels and limitations.
        Change the scenario to regenerate it.
      </SectionTitle>
      <div className="flex flex-wrap gap-2">
        <Button variant="solid" href={`${API}/api/report?${q}`} external>Open printable report ↗</Button>
        <Button href={`${API}/api/report?${q}&format=md`} external>Download Markdown</Button>
      </div>
      {err && <ErrorState message={err} onRetry={() => setN((x) => x + 1)} />}
      {!html && !err && <Spinner label="Building the report…" />}
      {html && (
        <GlassPanel className="overflow-hidden">
          <iframe title="Report preview" srcDoc={html} className="h-[75vh] w-full border-0 bg-transparent" />
        </GlassPanel>
      )}
      <p className="text-xs text-ink-mute">The preview uses the dashboard theme. The printable version opens as a plain white document for printing or saving as PDF.</p>
    </div>
  );
}
