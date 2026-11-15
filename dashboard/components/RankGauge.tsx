/** Circular gauge for the app-generated relevance score (0-100). Never an official NASA score. */
export default function RankGauge({ score, size = 64 }: { score: number; size?: number }) {
  const r = (size - 8) / 2, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  return (
    <div className="shrink-0 text-center" title="App-generated relevance (0-100), not an official NASA score">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" aria-hidden>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,.15)" strokeWidth="5" />
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#b4ecce" strokeWidth="5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} />
        </svg>
        <span className="num absolute inset-0 flex items-center justify-center text-lg font-[545] tracking-[-0.03em]">{score}</span>
      </div>
      <p className="mt-1 text-[10px] uppercase tracking-[.12em] text-ink-mute">relevance</p>
    </div>
  );
}
