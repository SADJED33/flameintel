"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, ApiFail } from "@/lib/api";
import type { ChatResult, Source } from "@/lib/types";
import { useScenario } from "@/lib/scenario";
import AnswerBody from "@/components/AnswerBody";
import SourceDrawer from "@/components/SourceDrawer";
import { OutcomeBadge } from "@/components/Badges";
import { Button, GlassPanel, ScenarioSelect, SectionTitle, Skeleton } from "@/components/ui";

const SUGGESTED = [
  "What channels did the SAFFIRE smoke detector record?",
  "Which experiments studied flame spread over solid materials?",
  "What materials were burned in SAFFIRE-III and at what airflow?",
  "What does the SPICE experiment measure?",
  "How does oxygen concentration relate to flame extinguishment in FLEX?",
  "What smoke or aerosol measurements were made in SAME?",
  "Which data files exist for the cool flames investigations?",
  "Is there data on water-mist fire suppression?",
];

type Msg = {
  id: number; q: string; scenario: string; status: "loading" | "done" | "error";
  result?: ChatResult; error?: { type: string; message: string; retryAfter?: number | null }; t0: number;
};

function Elapsed({ t0 }: { t0: number }) {
  const [s, setS] = useState(0);
  useEffect(() => { const i = setInterval(() => setS(Math.floor((Date.now() - t0) / 1000)), 500); return () => clearInterval(i); }, [t0]);
  return <span className="num text-ink-mute">{s}s</span>;
}

export default function AssistantPage() {
  const { scenario } = useScenario();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<{ msg: number; id: string } | null>(null);
  const busy = msgs.some((m) => m.status === "loading");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs.length, msgs.at(-1)?.status]);
  // /assistant?q=... pre-fills the box (links from the details page); the user still presses Ask
  useEffect(() => { const pre = new URLSearchParams(window.location.search).get("q"); if (pre) setQ(pre); }, []);

  async function ask(question: string) {
    const text = question.trim();
    if (text.length < 3 || busy) return;
    const id = Date.now();
    setQ("");
    setMsgs((m) => [...m, { id, q: text, scenario, status: "loading", t0: Date.now() }]);
    try {
      const result = await api<ChatResult>("/api/chat", { method: "POST", body: JSON.stringify({ question: text, scenario }), timeoutMs: 75000 });
      setMsgs((m) => m.map((x) => (x.id === id ? { ...x, status: "done", result } : x)));
    } catch (e) {
      const f = e as ApiFail;
      setMsgs((m) => m.map((x) => (x.id === id ? { ...x, status: "error", error: { type: f.type, message: f.message, retryAfter: f.retryAfter } } : x)));
    }
  }

  const openSource: Source | undefined = open ? msgs.find((m) => m.id === open.msg)?.result?.sources.find((s) => s.id === open.id) : undefined;

  return (
    <div className={`mx-auto max-w-3xl transition-[margin] duration-300 ${openSource ? "xl:mr-[470px]" : ""}`}>
      <div className="space-y-8">
        <SectionTitle eyebrow="AI Research Assistant" title="Ask the research, get cited answers" right={<ScenarioSelect />}>
          Answers come only from the indexed NASA PSI sources (24 experiments). Every factual sentence carries an <span className="rounded-full border border-mint/50 bg-mint/10 px-2 text-[12px] font-medium text-mint">S#</span> tag
          you can open. When the sources do not cover a question, the assistant says so instead of guessing. The scenario <b className="font-medium text-white">{scenario}</b> is background only, never evidence.
        </SectionTitle>

        {msgs.length === 0 && (
          <div>
            <p className="eyebrow mb-3">Try one of these</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED.map((s) => <button key={s} onClick={() => ask(s)} className="chip text-left">{s}</button>)}
            </div>
          </div>
        )}

        <div className="space-y-8">
          {msgs.map((m) => (
            <article key={m.id} className="rise space-y-3" aria-live="polite">
              <div className="flex justify-end">
                <p className="glass max-w-[85%] rounded-[14px] rounded-tr-sm px-4 py-2.5 text-sm">{m.q}</p>
              </div>

              {m.status === "loading" && (
                <GlassPanel className="p-5" role="status">
                  <p className="mb-3 text-sm text-ink-dim">Thinking, up to 45 s… <Elapsed t0={m.t0} /> <span className="text-ink-mute">(retrieving sources, then asking the language model)</span></p>
                  <Skeleton lines={4} />
                </GlassPanel>
              )}

              {m.status === "error" && m.error && (
                <GlassPanel className="border-warm/40 p-5" role="alert">
                  <p className="font-medium text-warm">{m.error.type === "quota" || m.error.type === "rate_limit" ? "The assistant is busy" : "The assistant could not answer"}</p>
                  <p className="mt-1 text-sm text-ink-dim">{m.error.message}</p>
                  <Button size="sm" className="mt-3" disabled={busy} onClick={() => ask(m.q)}>Try again</Button>
                </GlassPanel>
              )}

              {m.status === "done" && m.result && (
                <GlassPanel className={`p-5 sm:p-6 ${m.result.outcome === "refused" ? "!border-warm/40" : ""}`}>
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    <OutcomeBadge outcome={m.result.outcome} />
                    {m.result.model && <span className="pill !py-1 font-mono !text-[11px]" title="Model that wrote this answer">{m.result.model}</span>}
                    {m.result.cache_hit && <span className="pill !py-1 !text-[11px]" title="Same question and same sources were answered before; no model call">cached answer</span>}
                    <span className="num ml-auto text-[11.5px] text-ink-mute">{m.result.timing_s}s · {m.result.sources.length} sources</span>
                  </div>

                  {m.result.model_switched && (
                    <div className="mb-4 rounded-btn border border-violet/60 bg-violet/15 px-3 py-2 text-xs text-white">
                      Switched model: the preferred model was rate-limited or slow, so this answer was written by <span className="font-mono">{m.result.model}</span>.
                    </div>
                  )}

                  <AnswerBody answer={m.result.answer} sources={m.result.sources} onCite={(id) => setOpen({ msg: m.id, id })} />

                  {m.result.warnings.length > 0 && (
                    <div className="mt-4 rounded-btn border border-warm/50 bg-warm/10 p-3" role="note">
                      <p className="text-sm font-medium text-warm">Number check: verify these against the source</p>
                      <ul className="mt-1.5 space-y-1.5 text-xs text-ink-dim">
                        {m.result.warnings.map((w, i) => (
                          <li key={i}>
                            <span className="text-warm">{w.issue}{w.numbers.length ? `: ${w.numbers.join(", ")}` : ""}</span>
                            <span className="block text-ink-mute">“{w.text.replace(/\*\*/g, "")}”</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {m.result.related.length > 0 && (
                    <div className="mt-5">
                      <p className="eyebrow mb-2">Related experiments</p>
                      <div className="flex flex-wrap gap-2">
                        {m.result.related.map((r) => (
                          <Link key={r.psi} href={`/investigations/${r.psi}`} className="chip" title={r.title}>{r.psi}{r.acronym ? ` · ${r.acronym}` : ""}</Link>
                        ))}
                      </div>
                    </div>
                  )}

                  {m.result.sources.length > 0 && (
                    <details className="mt-5 text-sm">
                      <summary className="cursor-pointer text-ink-dim transition-colors hover:text-white">All {m.result.sources.length} sources the model saw</summary>
                      <ul className="mt-2 divide-y divide-white/10 rounded-btn border border-white/15">
                        {m.result.sources.map((s) => (
                          <li key={s.id}>
                            <button onClick={() => setOpen({ msg: m.id, id: s.id })} className="flex w-full items-center gap-3 px-3 py-2 text-left text-xs transition-colors hover:bg-white/[.07]">
                              <span className="font-medium text-mint">{s.id}</span>
                              <span className="font-medium">{s.psi}{s.acronym ? ` · ${s.acronym}` : ""}</span>
                              <span className="truncate text-ink-mute">{s.doc_type} · {s.loc}</span>
                              <span className="num ml-auto text-ink-mute">{s.distance.toFixed(3)}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </GlassPanel>
              )}
            </article>
          ))}
          <div ref={endRef} />
        </div>

        <form className="sticky bottom-4 z-20" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <div className="pop flex items-end gap-2 p-2">
            <textarea
              value={q} onChange={(e) => setQ(e.target.value)} rows={1} maxLength={1000} disabled={busy}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(q); } }}
              placeholder={busy ? "Waiting for the answer…" : "Ask about a NASA PSI combustion experiment…"} aria-label="Your question"
              className="max-h-32 min-h-[42px] flex-1 resize-none bg-transparent px-3 py-2.5 text-sm text-white placeholder:text-ink-mute focus:outline-none"
            />
            <Button type="submit" variant="solid" disabled={busy || q.trim().length < 3}>Ask</Button>
          </div>
          {msgs.length > 0 && !busy && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {SUGGESTED.slice(0, 3).map((s) => <button type="button" key={s} onClick={() => ask(s)} className="chip !text-[11px]">{s}</button>)}
            </div>
          )}
        </form>
      </div>
      <SourceDrawer source={openSource} onClose={() => setOpen(null)} />
    </div>
  );
}
