import type { HTMLAttributes, ReactNode } from "react";

type P = { children: ReactNode; className?: string } & Omit<HTMLAttributes<HTMLElement>, "className">;

/** Light glass (landing pill/header look): background .12 + 1px .15 border + blur(10px) saturate(140%). */
export function GlassCard({ children, className = "", ...rest }: P) {
  return <div className={`glass rounded-panel ${className}`} {...rest}>{children}</div>;
}

/** Dense glass on a dark base: use for tables, charts, citations and long answers (small text never sits on the artwork). */
export function GlassPanel({ children, className = "", ...rest }: P) {
  return <div className={`panel ${className}`} {...rest}>{children}</div>;
}
