/** Same logo SVG as the landing page (viewBox 0 0 26.9 16.6). */
export function FlameMark({ size = 27 }: { size?: number }) {
  return (
    <svg viewBox="0 0 26.9 16.6" width={size} height={(size * 16.6) / 26.9} fill="none" aria-hidden style={{ overflow: "visible" }}>
      <ellipse cx="13.25" cy="8.4" rx="13.2" ry="2.9" transform="rotate(-25 13.25 8.4)" stroke="currentColor" strokeWidth="1.25" />
      <circle cx="13.25" cy="8.4" r="8.8" fill="#000" />
      <circle cx="13.25" cy="8.4" r="8.1" fill="currentColor" />
      <ellipse cx="13.25" cy="8.4" rx="13.2" ry="2.9" transform="rotate(-25 13.25 8.4)" stroke="#000" strokeWidth="0.9" strokeDasharray="28.2 28.2" />
      <ellipse cx="13.25" cy="8.4" rx="13.2" ry="2.9" transform="rotate(-25 13.25 8.4)" stroke="currentColor" strokeWidth="1.25" strokeDasharray="28.2 28.2" />
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-[11px] text-white/[.98] ${className}`}>
      <FlameMark />
      <span className="text-[18px] font-[550] leading-none [font-variation-settings:'opsz'_22]">FlameIntel</span>
    </span>
  );
}
