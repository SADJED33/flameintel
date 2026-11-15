"use client";
import { SCENARIOS, useScenario } from "@/lib/scenario";

/** Scenario picker (glass select) used in the header area of every scenario-aware page. */
export default function ScenarioSelect() {
  const { scenario, setScenario } = useScenario();
  return (
    <label className="flex items-center gap-2.5">
      <span className="eyebrow !tracking-[0.12em]">Scenario</span>
      <select value={scenario} onChange={(e) => setScenario(e.target.value as (typeof SCENARIOS)[number])} className="input !h-9 !w-auto min-w-[180px] cursor-pointer !py-0 text-[13px]" aria-label="Scenario">
        {SCENARIOS.map((s) => <option key={s}>{s}</option>)}
      </select>
    </label>
  );
}
