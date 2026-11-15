/**
 * Original astronaut illustration (drawn for FlameIntel; no agency logos, patches or flags).
 * The visor reflects the flame; a thin tether trails off behind.
 */
export default function Astronaut({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="-60 0 380 400" className={className} role="img" aria-label="An astronaut drifting in microgravity, looking at a spherical flame">
      <defs>
        <linearGradient id="suit" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f5f7fc" />
          <stop offset="0.55" stopColor="#cdd4e6" />
          <stop offset="1" stopColor="#8c96b4" />
        </linearGradient>
        <linearGradient id="suit2" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#aab3cc" />
          <stop offset="1" stopColor="#e8ecf6" />
        </linearGradient>
        <linearGradient id="pack" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#56607f" />
          <stop offset="1" stopColor="#8e98b4" />
        </linearGradient>
        <radialGradient id="visor" cx="0.3" cy="0.35" r="0.9">
          <stop offset="0" stopColor="#ffb25e" />
          <stop offset="0.22" stopColor="#c7531c" />
          <stop offset="0.55" stopColor="#2b2147" />
          <stop offset="1" stopColor="#0b0c1e" />
        </radialGradient>
        <linearGradient id="rim" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="rgba(255,120,40,.0)" />
          <stop offset="1" stopColor="rgba(255,140,60,.55)" />
        </linearGradient>
        <clipPath id="helmetClip"><circle cx="160" cy="84" r="52" /></clipPath>
      </defs>

      {/* tether */}
      <path d="M96 196 C 30 232, -6 300, -58 352" fill="none" stroke="#c8d0e4" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="1 0" opacity=".75" />
      <circle cx="96" cy="196" r="4" fill="#c8d0e4" />

      {/* legs */}
      <path d="M138 244 C 130 284, 114 306, 108 338" fill="none" stroke="url(#suit)" strokeWidth="36" strokeLinecap="round" />
      <path d="M186 244 C 196 282, 212 300, 222 326" fill="none" stroke="url(#suit)" strokeWidth="36" strokeLinecap="round" />
      <rect x="86" y="326" width="46" height="26" rx="12" transform="rotate(-8 109 339)" fill="#3a4263" />
      <rect x="200" y="316" width="46" height="26" rx="12" transform="rotate(26 223 329)" fill="#3a4263" />

      {/* backpack */}
      <rect x="92" y="134" width="44" height="104" rx="16" fill="url(#pack)" />
      <rect x="100" y="146" width="10" height="6" rx="2" fill="#ff6b1f" />
      <rect x="100" y="158" width="10" height="6" rx="2" fill="#6aa8ff" />

      {/* arm reaching toward the flame (viewer's left) */}
      <path d="M126 158 C 88 150, 56 128, 38 100" fill="none" stroke="url(#suit)" strokeWidth="30" strokeLinecap="round" />
      <circle cx="36" cy="96" r="17" fill="#e9edf8" stroke="#8c96b4" strokeWidth="2" />
      <path d="M28 88 q8 -8 16 0" fill="none" stroke="#8c96b4" strokeWidth="2" strokeLinecap="round" />

      {/* torso */}
      <rect x="112" y="124" width="104" height="124" rx="30" fill="url(#suit)" />
      <rect x="112" y="124" width="104" height="124" rx="30" fill="url(#rim)" />
      <ellipse cx="164" cy="246" rx="52" ry="10" fill="#9aa4c0" />
      {/* chest control box */}
      <rect x="138" y="162" width="52" height="38" rx="8" fill="#232a48" stroke="#8c96b4" strokeWidth="1.5" />
      <circle cx="150" cy="176" r="4" fill="#ff6b1f" />
      <circle cx="164" cy="176" r="4" fill="#6aa8ff" />
      <circle cx="178" cy="176" r="4" fill="#4fd1a5" />
      <rect x="146" y="187" width="36" height="5" rx="2.5" fill="#3b456d" />

      {/* relaxed arm (viewer's right) */}
      <path d="M208 158 C 238 178, 246 212, 234 240" fill="none" stroke="url(#suit)" strokeWidth="30" strokeLinecap="round" />
      <circle cx="232" cy="248" r="16" fill="#e9edf8" stroke="#8c96b4" strokeWidth="2" />

      {/* neck ring + helmet */}
      <ellipse cx="162" cy="130" rx="38" ry="10" fill="#aab3cc" />
      <circle cx="160" cy="84" r="54" fill="url(#suit)" />
      <circle cx="160" cy="84" r="54" fill="url(#rim)" />
      <ellipse cx="168" cy="88" rx="40" ry="35" fill="url(#visor)" stroke="#2a3150" strokeWidth="3" />
      <g clipPath="url(#helmetClip)">
        <ellipse cx="146" cy="70" rx="13" ry="7" fill="#fff" opacity=".35" transform="rotate(-28 146 70)" />
        <circle cx="190" cy="102" r="3" fill="#ffd9a8" opacity=".6" />
      </g>
      <rect x="150" y="30" width="20" height="8" rx="4" fill="#9aa4c0" />
    </svg>
  );
}
