import { AdvantageSection } from "../components/landing/AdvantageSection.jsx";
import { HeroSection } from "../components/landing/HeroSection.jsx";
import { ManualComparisonSection } from "../components/landing/ManualComparisonSection.jsx";
import { RiskRadarSection } from "../components/landing/RiskRadarSection.jsx";
import { WorkflowSection } from "../components/landing/WorkflowSection.jsx";

export function HomePage({ onNavigate }) {
  return (
    <section className="page page-home" aria-label="OllyUW overview">
      <HeroSection onNavigate={onNavigate} />
      <ManualComparisonSection />
      <RiskRadarSection onNavigate={onNavigate} />
      <AdvantageSection />
      <WorkflowSection onNavigate={onNavigate} />
    </section>
  );
}
