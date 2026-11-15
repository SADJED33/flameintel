import type { ReactNode } from "react";

export type Tone = "mint" | "violet" | "warm" | "white" | "neutral";

// solid chips (the landing "New" chip style): readable black / white text on the sampled artwork colours
const SOLID: Record<Tone, string> = {
  mint: "bg-mint text-black",
  violet: "bg-violet text-white",
  warm: "bg-warm text-black",
  white: "bg-white text-black",
  neutral: "bg-white/15 text-white",
};
// glass pills with a tinted border and dot
const GLASS: Record<Tone, string> = {
  mint: "border-mint/45 bg-mint/10",
  violet: "border-violet/60 bg-violet/15",
  warm: "border-warm/50 bg-warm/10",
  white: "border-white/35 bg-white/10",
  neutral: "",
};
const DOT: Record<Tone, string> = { mint: "bg-mint", violet: "bg-violet-ink", warm: "bg-warm", white: "bg-white", neutral: "bg-white/60" };

/** Pill: glass pill with a coloured dot (evidence labels, availability). */
export function Pill({ tone = "neutral", dot = true, title, children }: { tone?: Tone; dot?: boolean; title?: string; children: ReactNode }) {
  return (
    <span className={`tag-label ${GLASS[tone]}`} title={title}>
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${DOT[tone]}`} aria-hidden />}
      {children}
    </span>
  );
}

/** Chip: solid "New"-style chip (outcome badges: answered = mint, partial = violet, refused = warm). */
export function Chip({ tone = "white", title, children }: { tone?: Tone; title?: string; children: ReactNode }) {
  return <span className={`pill-chip ${SOLID[tone]}`} title={title}>{children}</span>;
}
