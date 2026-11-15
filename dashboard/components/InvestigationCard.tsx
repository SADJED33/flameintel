"use client";
import Link from "next/link";
import { useState } from "react";
import { AvailabilityBadge } from "./Badges";
import RankGauge from "./RankGauge";
import { Button, GlassPanel, Tag } from "./ui";
import type { Rank } from "@/lib/types";

export type Card = {
  id: string; acronym: string; title: string; name: string; description: string; topics: string[];
  environment: string; gravity_condition: string; availability: string; tabular_file_count: number;
  publication_count: number; source_url: string; source_url_note: string; materials: string[];
  index_chunk_total: number; rank?: Rank;
};

export default function InvestigationCard({
  c, scenario, selected, onToggle, compact = false,
}: { c: Card; scenario?: string; selected?: boolean; onToggle?: () => void; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <GlassPanel className={`flex h-full flex-col p-5 transition-colors hover:border-white/35 ${selected ? "!border-mint/60" : ""}`}>
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="num text-xs font-medium text-mint">{c.id}</span>
            <AvailabilityBadge value={c.availability} />
          </div>
          <h3 className="mt-2 text-xl leading-snug">
            <Link href={`/investigations/${c.id}`} className="hover:text-mint">{c.acronym || c.title}</Link>
          </h3>
          {c.acronym && <p className="mt-0.5 text-sm text-ink-dim">{c.title}</p>}
        </div>
        {c.rank && <RankGauge score={c.rank.score} />}
      </div>

      <p className="mt-3 text-sm leading-relaxed text-ink-dim">{c.description}</p>
      <p className="mt-1 text-[11px] text-ink-mute">Source-derived: first lines of the objective in the PSI record.</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {c.topics.map((t) => <Tag key={t}>{t}</Tag>)}
        <Tag active>{c.environment}</Tag>
        <Tag>{c.gravity_condition.split(" (")[0].replace("Ground-based / computational", "Ground / computational")}</Tag>
      </div>

      {!compact && (
        <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-mute">
          <span>{c.tabular_file_count} tabular file(s)</span>
          <span>{c.publication_count} publication(s)</span>
          <span>{c.index_chunk_total.toLocaleString("en-US")} indexed passages</span>
        </p>
      )}

      {c.rank && (
        <div className="mt-4 rounded-btn border border-white/15 bg-white/[.05]">
          <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-ink-dim transition-colors hover:text-white" aria-expanded={open}>
            <span>Why relevant? <span className="text-ink-mute">({scenario})</span></span>
            <span className="text-xs">{open ? "Hide" : "Show"}</span>
          </button>
          {open && (
            <div className="space-y-2.5 border-t border-white/15 px-3 py-3 text-sm">
              <ul className="space-y-1.5 text-ink-dim">
                {c.rank.why.map((w, i) => <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-mint" />{w}</li>)}
              </ul>
              <p className="rounded-btn border border-warm/40 bg-warm/10 px-3 py-2 text-xs text-warm">{c.rank.gravity_note}</p>
              <p className="text-[11px] text-ink-mute">{c.rank.disclaimer}</p>
            </div>
          )}
        </div>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-2 pt-4">
        <Button href={`/investigations/${c.id}`} size="sm">Details</Button>
        <Button href={c.source_url} external size="sm">Original PSI record ↗</Button>
        {onToggle && (
          <label className="ml-auto flex cursor-pointer items-center gap-2 text-xs text-ink-dim">
            <input type="checkbox" checked={!!selected} onChange={onToggle} className="h-4 w-4 accent-[#b4ecce]" /> Compare
          </label>
        )}
      </div>
    </GlassPanel>
  );
}
