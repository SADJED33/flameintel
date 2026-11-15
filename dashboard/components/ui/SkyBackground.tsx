"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

const POSTER = "/landing/assets/sky.webp";
const VIDEO = "/landing/assets/sky.mp4";
const VIDEO_PAGES = ["/dashboard", "/assistant"];            // video only here
const HEAVY_PAGES = ["/data", "/insights", "/compare", "/report", "/investigations", "/about"]; // data-dense: stronger veil

/**
 * Fixed full-screen artwork behind every dashboard page. Still image everywhere; the looping muted video only on
 * Overview and the Assistant. The video pauses when the tab is hidden and is never used with reduced motion.
 */
export default function SkyBackground() {
  const path = usePathname() || "";
  const wantVideo = VIDEO_PAGES.some((p) => path === p);
  const heavy = HEAVY_PAGES.some((p) => path.startsWith(p));
  const [reduced, setReduced] = useState(true); // start without video until we know
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    v.muted = true;
    const play = () => { if (v.paused && !document.hidden) v.play().catch(() => {}); };
    const vis = () => (document.hidden ? v.pause() : play());
    play();
    v.addEventListener("canplay", play);
    document.addEventListener("visibilitychange", vis);
    return () => { v.removeEventListener("canplay", play); document.removeEventListener("visibilitychange", vis); };
  }, [wantVideo, reduced]);

  const veil = heavy
    ? "linear-gradient(to bottom, rgba(0,0,0,.90) 0%, rgba(0,0,0,.80) 100%)"
    : "linear-gradient(to bottom, rgba(0,0,0,.82) 0%, rgba(0,0,0,.55) 100%)";

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-black" aria-hidden>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={POSTER} alt="" className="absolute inset-0 h-full w-full object-cover object-bottom" />
      {wantVideo && !reduced && (
        <video ref={ref} className="absolute inset-0 h-full w-full object-cover object-bottom" autoPlay muted loop playsInline preload="auto" poster={POSTER} src={VIDEO} />
      )}
      <div className="absolute inset-0" style={{ background: veil }} />
    </div>
  );
}
