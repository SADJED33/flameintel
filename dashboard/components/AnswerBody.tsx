"use client";
import React from "react";
import type { Source } from "@/lib/types";

const PARTIAL = /^results are not in the retrieved sources\.?$/i;
const MISSING = /^[*_\s-]*not in the data\s*:/i;
const NOT_IN = /^[*_\s-]*not in the data\.?[*_\s]*$/i;

// inline text: bold, the Observed / Context labels, and [S#] citations
function Inline({ text, sources, onCite }: { text: string; sources: Source[]; onCite: (id: string) => void }) {
  const known = new Set(sources.map((s) => s.id));
  const parts = text.split(/(\*\*[^*]+\*\*|\[S\d+\])/g).filter((p) => p !== "");
  return (
    <>
      {parts.map((p, i) => {
        const cite = p.match(/^\[(S\d+)\]$/);
        if (cite) {
          const id = cite[1];
          return known.has(id) ? (
            <button
              key={i} onClick={() => onCite(id)} title={`Open source ${id}`}
              className="mx-0.5 inline-flex -translate-y-px items-center rounded-full border border-mint/50 bg-mint/10 px-2 py-px text-[11px] font-medium text-mint transition-colors hover:bg-mint hover:text-black"
            >{id}</button>
          ) : (
            <span key={i} className="mx-0.5 rounded-full border border-warm/50 bg-warm/10 px-2 py-px text-[11px] text-warm" title="This tag does not match any retrieved source">{id}?</span>
          );
        }
        const b = p.match(/^\*\*([^*]+)\*\*$/);
        if (b) {
          const label = b[1].replace(/:$/, "");
          if (label === "Observed")
            return <span key={i} className="mr-1.5 rounded-full bg-mint px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-black" title="A result or test condition stated in the source">Observed</span>;
          if (label === "Context")
            return <span key={i} className="mr-1.5 rounded-full bg-violet px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white" title="Background, objective or description, not a result">Context</span>;
          return <strong key={i} className="font-semibold text-white">{b[1]}</strong>;
        }
        // text right after an Observed/Context label starts with ":" in the model's output: drop it
        const prev = parts[i - 1] || "";
        const afterLabel = /^\*\*(Observed|Context):?\*\*$/.test(prev);
        return <React.Fragment key={i}>{afterLabel ? p.replace(/^\s*:\s*/, "") : p}</React.Fragment>;
      })}
    </>
  );
}

export default function AnswerBody({ answer, sources, onCite }: { answer: string; sources: Source[]; onCite: (id: string) => void }) {
  // the "Related experiments:" list is rendered separately from the structured `related` field
  const cut = answer.search(/\n*Related experiments:/i);
  const body = (cut >= 0 ? answer.slice(0, cut) : answer).trim();
  const lines = body.split("\n").map((l) => l.trim()).filter(Boolean);
  return (
    <div className="space-y-3 text-[15px] leading-relaxed text-white [font-variation-settings:'opsz'_20]">
      {lines.map((raw, i) => {
        const plain = raw.replace(/^[*\-•]\s+/, "");
        const flat = plain.replace(/\*\*/g, "").trim();
        if (NOT_IN.test(plain)) {
          return (
            <div key={i} className="rounded-btn border border-warm/50 bg-warm/10 px-4 py-3">
              <p className="text-lg font-[545] text-warm [font-variation-settings:'opsz'_22]">Not in the data.</p>
              <p className="mt-0.5 text-sm text-ink-dim">The knowledge base has nothing that supports an answer, so none is given.</p>
            </div>
          );
        }
        if (MISSING.test(plain)) {
          return (
            <div key={i} className="rounded-btn border border-warm/50 bg-warm/10 px-4 py-2.5 text-sm">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-warm">Not in the data</span>
              <p className="mt-0.5 text-white">{flat.replace(/^not in the data\s*:\s*/i, "")}</p>
            </div>
          );
        }
        if (PARTIAL.test(flat)) {
          return (
            <p key={i} className="rounded-btn border border-white/15 bg-white/[.07] px-4 py-2.5 text-sm italic text-ink-dim">
              {flat} <span className="not-italic text-ink-mute">The sources describe the experiment but do not report results for what you asked.</span>
            </p>
          );
        }
        const isBullet = /^[*\-•]\s+/.test(raw);
        return (
          <p key={i} className={isBullet ? "flex gap-2.5" : ""}>
            {isBullet && <span className="mt-[10px] h-1.5 w-1.5 shrink-0 rounded-full bg-mint" aria-hidden />}
            <span><Inline text={plain} sources={sources} onCite={onCite} /></span>
          </p>
        );
      })}
    </div>
  );
}
