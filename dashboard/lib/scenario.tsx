"use client";
import { createContext, useContext, useEffect, useState } from "react";

export const SCENARIOS = ["Spacecraft", "ISS", "Lunar Habitat", "Mars Habitat", "Pressurized Rover"] as const;
export type Scenario = (typeof SCENARIOS)[number];

const Ctx = createContext<{ scenario: Scenario; setScenario: (s: Scenario) => void }>({
  scenario: "Lunar Habitat",
  setScenario: () => {},
});

export function ScenarioProvider({ children }: { children: React.ReactNode }) {
  const [scenario, setS] = useState<Scenario>("Lunar Habitat");
  useEffect(() => {
    try {
      const v = localStorage.getItem("fi.scenario");
      if (v && (SCENARIOS as readonly string[]).includes(v)) setS(v as Scenario);
    } catch {}
  }, []);
  const setScenario = (s: Scenario) => {
    setS(s);
    try { localStorage.setItem("fi.scenario", s); } catch {}
  };
  return <Ctx.Provider value={{ scenario, setScenario }}>{children}</Ctx.Provider>;
}
export const useScenario = () => useContext(Ctx);
