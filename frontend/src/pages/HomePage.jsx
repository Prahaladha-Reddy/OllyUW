import { AdvantageSection } from '../components/landing/AdvantageSection'
import { HeroSection } from '../components/landing/HeroSection'
import { ManualComparisonSection } from '../components/landing/ManualComparisonSection'
import { RiskRadarSection } from '../components/landing/RiskRadarSection'
import { WorkflowSection } from '../components/landing/WorkflowSection'

export function HomePage() {
  return (
    <section className="page page-home" aria-label="OllyUW overview">
      <HeroSection />
      <ManualComparisonSection />
      <RiskRadarSection />
      <AdvantageSection />
      <WorkflowSection />
    </section>
  )
}
