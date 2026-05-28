import { AdvantageSection } from '../components/landing/AdvantageSection'
import { HeroSection } from '../components/landing/HeroSection'
import { WorkflowSection } from '../components/landing/WorkflowSection'

export function HomePage() {
  return (
    <section className="page page-home" aria-label="Olly overview">
      <HeroSection />
      <AdvantageSection />
      <WorkflowSection />
    </section>
  )
}
