import type { ReactNode } from "react";
import { Chip, Pill, type Tone } from "./ui/Pill";
import { EmptyState, ErrorState, Skeleton } from "./ui/Basics";

export type EvidenceKind = "source_reported" | "app_interpretation" | "potential_application";

export const EVIDENCE: Record<EvidenceKind, { label: string; tone: Tone; help: string }> = {
  source_reported: { label: "Source-reported", tone: "mint", help: "Explicitly stated in a NASA PSI source." },
  app_interpretation: { label: "FlameIntel interpretation", tone: "violet", help: "The app's own relevance analysis. Not a NASA statement." },
  potential_application: { label: "Potential application", tone: "white", help: "A possible future use that needs validation. Not a certification." },
};

/** Evidence labels are Pills (glass pill + coloured dot). */
export function EvidenceLabel({ kind }: { kind: EvidenceKind }) {
  const e = EVIDENCE[kind];
  return <Pill tone={e.tone} title={e.help}>{e.label}</Pill>;
}

const OUTCOME = {
  answered: { label: "Answered", tone: "mint" as Tone, help: "The sources answer the question." },
  partial: { label: "Partial", tone: "violet" as Tone, help: "Some part of the question is not supported by the sources." },
  refused: { label: "Refused", tone: "warm" as Tone, help: "Nothing in the knowledge base answers this (or the request was not allowed), so the assistant declined." },
} as const;

/** Outcome badge: solid chip, answered = mint, partial = violet, refused = warm. */
export function OutcomeBadge({ outcome }: { outcome: keyof typeof OUTCOME }) {
  const o = OUTCOME[outcome];
  return <Chip tone={o.tone} title={o.help}>{o.label}</Chip>;
}

const AVAIL: Record<string, { label: string; tone: Tone }> = {
  both: { label: "Dataset + publications", tone: "mint" },
  dataset: { label: "Dataset", tone: "mint" },
  publication: { label: "Publications", tone: "violet" },
  metadata_only: { label: "Metadata only", tone: "neutral" },
};
export function AvailabilityBadge({ value }: { value: string }) {
  const a = AVAIL[value] || AVAIL.metadata_only;
  return <Pill tone={a.tone}>{a.label}</Pill>;
}
export const AVAIL_LABEL = (v: string) => (AVAIL[v] || AVAIL.metadata_only).label;

export function DemoBadge({ children = "Demo data" }: { children?: ReactNode }) {
  return <Pill tone="warm">{children}</Pill>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" className="panel p-5">
      {label && <p className="mb-3 text-sm text-ink-dim">{label}</p>}
      <Skeleton lines={3} />
    </div>
  );
}
export const ErrorBox = ErrorState;
export const Empty = EmptyState;
