import { SiteHeader, SkyBackground } from "@/components/ui";
import { ScenarioProvider } from "@/lib/scenario";

export default function DashLayout({ children }: { children: React.ReactNode }) {
  return (
    <ScenarioProvider>
      <SkyBackground />
      <SiteHeader />
      <main className="page-enter mx-auto w-full max-w-[1280px] px-4 pb-16 pt-8 sm:px-6 lg:px-8 lg:pt-10">{children}</main>
      <footer className="no-print border-t border-line bg-black/50 px-4 py-6 text-center text-xs leading-relaxed text-ink-mute [-webkit-backdrop-filter:blur(10px)] [backdrop-filter:blur(10px)]">
        FlameIntel organizes existing NASA PSI research. It does not run experiments, replace NASA sources, or certify equipment. Not a NASA product.
      </footer>
    </ScenarioProvider>
  );
}
