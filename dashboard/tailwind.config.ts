import type { Config } from "tailwindcss";

// every colour reads the CSS variables in styles/tokens.css, so the tokens stay the single source
const rgb = (v: string) => `rgb(var(${v}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#000000",
        ink: { DEFAULT: "#ffffff", nav: "var(--ink-nav)", dim: "var(--ink-dim)", mute: "var(--ink-mute)", sub: "var(--ink-sub)" },
        mint: { DEFAULT: rgb("--mint-rgb"), deep: rgb("--mint-deep-rgb") },
        violet: { DEFAULT: rgb("--violet-rgb"), deep: rgb("--violet-deep-rgb"), ink: rgb("--violet-ink-rgb") },
        warm: rgb("--warm-rgb"),
        glass: "var(--glass-bg)",
        line: "var(--glass-line)",
        // legacy names still referenced by the retired React landing: alias to the new palette
        ember: { DEFAULT: rgb("--mint-rgb"), soft: rgb("--mint-rgb"), glow: rgb("--mint-rgb"), deep: rgb("--mint-deep-rgb") },
        space: { 900: "#000000", 800: "#0a0a0f", 700: "#14141b", 600: "#1c1c26", 500: "#262633" },
      },
      fontFamily: {
        sans: ["InterVar", "Inter", "Helvetica Neue", "Arial", "system-ui", "sans-serif"],
        display: ["InterVar", "Inter", "Helvetica Neue", "Arial", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: { btn: "var(--r-btn)", panel: "var(--r-panel)" },
      boxShadow: { pop: "var(--shadow-pop)", ember: "none", card: "none" },
      transitionTimingFunction: { soft: "var(--e-soft)", nav: "var(--e-nav)", reveal: "var(--e-reveal)" },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(12px)" }, to: { opacity: "1", transform: "none" } },
        pulseDot: { "0%,100%": { opacity: ".35" }, "50%": { opacity: "1" } },
        slideIn: { from: { transform: "translateX(24px)", opacity: "0" }, to: { transform: "none", opacity: "1" } },
        astro: { "0%,100%": { transform: "translate(0,0)" }, "50%": { transform: "translate(-22px,-30px)" } },
      },
      animation: {
        rise: "rise .6s cubic-bezier(.22,1,.36,1) both",
        dot: "pulseDot 1.2s ease-in-out infinite",
        slideIn: "slideIn .3s cubic-bezier(.33,1,.68,1) both",
      },
    },
  },
  plugins: [],
};
export default config;
