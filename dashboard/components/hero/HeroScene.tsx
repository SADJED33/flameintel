"use client";
import { useEffect, useRef } from "react";

/**
 * Full-screen canvas scene: parallax starfield, a spherical (microgravity) flame with a blue shell,
 * solar-flare style plasma arcs and drifting embers. One requestAnimationFrame loop.
 *  - DPR capped at 1.5, particle counts capped, adaptive quality when frames get slow
 *  - paused when the tab is hidden or the hero is off screen
 *  - prefers-reduced-motion: a single still frame, no loop, no mouse parallax
 */
type Star = { x: number; y: number; z: number; r: number; p: number; s: number };
type Arc = { a: number; span: number; h: number; born: number; dur: number; dir: number; seed: number };
type Ember = { a: number; d: number; v: number; life: number; age: number; size: number; w: number };

function rng(seed: number) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

export default function HeroScene({ astroRef }: { astroRef: React.RefObject<HTMLDivElement | null> }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current!;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const rand = rng(20260);
    const stars: Star[] = Array.from({ length: 230 }, () => ({
      x: rand(), y: rand(), z: 0.15 + rand() * 0.85, r: 0.4 + rand() * 1.3, p: rand() * 6.28, s: 0.6 + rand() * 2,
    }));
    const arcs: Arc[] = [];
    const MAX_ARCS = 8, MAX_EMBERS = 70;
    const newArc = (born: number, i: number): Arc => ({
      a: rand() * 6.283, span: 0.4 + rand() * 0.75, h: 0.55 + rand() * 1.1, born, dur: 4.5 + rand() * 4.5,
      dir: rand() < 0.5 ? -1 : 1, seed: rand() * 100 + i,
    });
    for (let i = 0; i < MAX_ARCS; i++) arcs.push(newArc(-rand() * 6, i));
    const embers: Ember[] = Array.from({ length: MAX_EMBERS }, () => ({
      a: rand() * 6.283, d: 1, v: 8 + rand() * 26, life: 2.5 + rand() * 4, age: rand() * 5, size: 0.7 + rand() * 1.9, w: rand() * 6.28,
    }));

    let w = 0, h = 0, dpr = 1, raf = 0, running = false, last = 0, time = reduce ? 4.2 : 0;
    let quality = 1, slow = 0, frames = 0;
    const m = { x: 0, y: 0, tx: 0, ty: 0 };

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      w = cv.clientWidth; h = cv.clientHeight;
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (reduce) frame(0);
    }

    function flameGeom() {
      const narrow = w < 820;
      const R = Math.min(w * (narrow ? 0.42 : 0.9), h * (narrow ? 0.9 : 1)) * (narrow ? 0.3 : 0.16);
      return { R, cx: (narrow ? w * 0.5 : w * 0.67) - m.x * 16, cy: (narrow ? h * 0.2 : h * 0.47) - m.y * 12 };
    }

    function drawStars(t: number) {
      const c = ctx!;
      for (const s of stars) {
        let x = (s.x * w - t * 5 * s.z + m.x * 26 * s.z) % w;
        if (x < 0) x += w;
        const y = s.y * h + m.y * 18 * s.z;
        const tw = 0.55 + 0.45 * Math.sin(t * s.s + s.p);
        c.globalAlpha = (0.25 + 0.65 * s.z) * tw;
        c.fillStyle = s.z > 0.8 ? "#ffe9cf" : s.z > 0.5 ? "#dfe8ff" : "#b8c4ee";
        c.beginPath(); c.arc(x, y, s.r * (0.6 + s.z * 0.7), 0, 6.283); c.fill();
      }
      c.globalAlpha = 1;
    }

    function drawArc(a: Arc, t: number, cx: number, cy: number, R: number) {
      const c = ctx!;
      const age = t - a.born, k = age / a.dur;
      if (k < 0 || k > 1) return;
      const grow = Math.min(1, k * 2.6), grow2 = 1 - Math.pow(1 - grow, 3);
      const alpha = Math.pow(Math.sin(Math.PI * k), 0.75);
      const A = a.a + Math.sin(t * 0.15 + a.seed) * 0.08, B = A + a.span * a.dir;
      const pt = (ang: number, rr: number) => [cx + Math.cos(ang) * rr, cy + Math.sin(ang) * rr];
      const wob = Math.sin(t * 1.3 + a.seed) * 0.12;
      const p0 = pt(A, R * 0.92), p3 = pt(B, R * 0.92);
      const p1 = pt(A + a.span * a.dir * (0.18 + wob), R * (1 + a.h * 1.25)), p2 = pt(A + a.span * a.dir * (0.82 - wob), R * (1 + a.h * 1.25));
      const N = 34, n = Math.max(2, Math.floor(N * grow2));
      const P: number[][] = [];
      for (let i = 0; i <= n; i++) {
        const u = (i / N), v = 1 - u;
        P.push([
          v * v * v * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u * u * u * p3[0],
          v * v * v * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u * u * u * p3[1],
        ]);
      }
      const passes: [number, string][] = [
        [R * 0.1, `rgba(255,90,20,${0.05 * alpha})`],
        [R * 0.045, `rgba(255,140,50,${0.22 * alpha})`],
        [R * 0.014 + 0.6, `rgba(255,226,170,${0.9 * alpha})`],
      ];
      c.lineCap = "round"; c.lineJoin = "round";
      for (const [lw, col] of passes) {
        c.lineWidth = lw; c.strokeStyle = col;
        c.beginPath(); c.moveTo(P[0][0], P[0][1]);
        for (let i = 1; i < P.length; i++) c.lineTo(P[i][0], P[i][1]);
        c.stroke();
      }
      // beads of plasma sliding along the loop
      for (let b = 0; b < 3; b++) {
        const q = ((k * 1.3 + b / 3) % 1) * (P.length - 1);
        const pi = P[Math.floor(q)];
        if (!pi) continue;
        const g = c.createRadialGradient(pi[0], pi[1], 0, pi[0], pi[1], R * 0.09);
        g.addColorStop(0, `rgba(255,240,200,${0.9 * alpha})`); g.addColorStop(1, "rgba(255,120,30,0)");
        c.fillStyle = g; c.beginPath(); c.arc(pi[0], pi[1], R * 0.09, 0, 6.283); c.fill();
      }
    }

    function drawFlame(t: number, cx: number, cy: number, R: number) {
      const c = ctx!;
      const pulse = 1 + 0.028 * Math.sin(t * 1.7) + 0.014 * Math.sin(t * 3.1 + 1);
      const r = R * pulse;
      // far halo
      let g = c.createRadialGradient(cx, cy, r * 0.4, cx, cy, r * 3.4);
      g.addColorStop(0, "rgba(255,110,30,.26)"); g.addColorStop(0.35, "rgba(255,80,20,.08)"); g.addColorStop(1, "rgba(255,80,20,0)");
      c.fillStyle = g; c.fillRect(cx - r * 3.5, cy - r * 3.5, r * 7, r * 7);
      // blue shell (a microgravity diffusion flame is a blue sphere with a glowing core)
      g = c.createRadialGradient(cx, cy, r * 0.9, cx, cy, r * 1.45);
      g.addColorStop(0, "rgba(120,170,255,0)"); g.addColorStop(0.3, "rgba(110,168,255,.30)"); g.addColorStop(1, "rgba(110,168,255,0)");
      c.fillStyle = g; c.beginPath(); c.arc(cx, cy, r * 1.45, 0, 6.283); c.fill();
      // body
      g = c.createRadialGradient(cx - r * 0.1, cy - r * 0.1, 0, cx, cy, r * 1.08);
      g.addColorStop(0, "rgba(255,248,226,1)"); g.addColorStop(0.28, "rgba(255,206,120,.98)");
      g.addColorStop(0.62, "rgba(255,120,36,.95)"); g.addColorStop(0.9, "rgba(210,70,14,.7)"); g.addColorStop(1, "rgba(160,40,10,0)");
      c.fillStyle = g; c.beginPath(); c.arc(cx, cy, r * 1.08, 0, 6.283); c.fill();
      // flicker blobs inside the sphere
      c.globalCompositeOperation = "lighter";
      for (let i = 0; i < 5; i++) {
        const a = t * (0.35 + i * 0.11) + i * 1.9, d = r * (0.28 + 0.16 * Math.sin(t * 0.7 + i));
        const bx = cx + Math.cos(a) * d, by = cy + Math.sin(a * 1.2) * d, br = r * (0.34 + 0.06 * Math.sin(t * 2 + i));
        const gg = c.createRadialGradient(bx, by, 0, bx, by, br);
        gg.addColorStop(0, "rgba(255,226,160,.5)"); gg.addColorStop(1, "rgba(255,140,40,0)");
        c.fillStyle = gg; c.beginPath(); c.arc(bx, by, br, 0, 6.283); c.fill();
      }
      c.globalCompositeOperation = "source-over";
    }

    function drawEmbers(dt: number, cx: number, cy: number, R: number) {
      const c = ctx!;
      const n = Math.floor(MAX_EMBERS * quality);
      for (let i = 0; i < n; i++) {
        const e = embers[i];
        e.age += dt;
        if (e.age > e.life) { e.age = 0; e.a = Math.random() * 6.283; e.d = 1.02; e.life = 2.5 + Math.random() * 4; e.v = 8 + Math.random() * 26; }
        e.d += (e.v * dt) / R * 0.5;
        const k = e.age / e.life, ang = e.a + Math.sin(e.age * 1.4 + e.w) * 0.12;
        const x = cx + Math.cos(ang) * R * e.d, y = cy + Math.sin(ang) * R * e.d;
        c.globalAlpha = Math.sin(Math.PI * k) * 0.85;
        c.fillStyle = k < 0.5 ? "#ffd08a" : "#ff7a2a";
        c.beginPath(); c.arc(x, y, e.size * (1 - k * 0.5), 0, 6.283); c.fill();
      }
      c.globalAlpha = 1;
    }

    function frame(dt: number) {
      const c = ctx!;
      time += dt;
      m.x += (m.tx - m.x) * 0.05; m.y += (m.ty - m.y) * 0.05;
      c.clearRect(0, 0, w, h);
      drawStars(time);
      const { R, cx, cy } = flameGeom();
      drawFlame(time, cx, cy, R);
      c.globalCompositeOperation = "lighter";
      const na = Math.max(3, Math.floor(MAX_ARCS * quality));
      for (let i = 0; i < na; i++) {
        const a = arcs[i];
        if (time - a.born > a.dur) arcs[i] = newArc(time + Math.random() * 0.5, i);
        drawArc(arcs[i], time, cx, cy, R);
      }
      drawEmbers(dt, cx, cy, R);
      c.globalCompositeOperation = "source-over";
      const el = astroRef.current;
      if (el) { el.style.setProperty("--px", String(m.x * -22)); el.style.setProperty("--py", String(m.y * -16)); }
    }

    function loop(now: number) {
      if (!running) return;
      const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
      last = now;
      // adaptive quality: if frames stay slower than ~26 ms, shed particles
      frames++; if (dt > 0.026) slow++;
      if (frames >= 90) { if (slow > 45 && quality > 0.4) quality -= 0.2; frames = 0; slow = 0; }
      frame(dt);
      raf = requestAnimationFrame(loop);
    }
    const start = () => { if (reduce || running || document.hidden) return; running = true; last = performance.now(); raf = requestAnimationFrame(loop); };
    const stop = () => { running = false; cancelAnimationFrame(raf); };

    const onMove = (e: PointerEvent) => { if (reduce) return; m.tx = (e.clientX / window.innerWidth - 0.5) * 2; m.ty = (e.clientY / window.innerHeight - 0.5) * 2; };
    const onVis = () => (document.hidden ? stop() : start());
    const io = new IntersectionObserver(([en]) => (en.isIntersecting ? start() : stop()), { threshold: 0.01 });
    io.observe(cv);
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("visibilitychange", onVis);
    resize();
    start();
    return () => {
      stop(); io.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [astroRef]);

  return <canvas ref={ref} className="absolute inset-0 h-full w-full" aria-hidden />;
}
