import { Link } from 'react-router-dom'
import { RadarChart } from './RadarChart'

export function RiskRadarSection() {
  return (
    <section className="risk-section section-cream">
      <div className="split-layout">
        <div className="sticky-copy">
          <p className="eyebrow">What OllyUW Scores</p>
          <h2>A 12-part view of AI agent liability.</h2>
          <p>
            OllyUW scores each dimension from 0 to 10 and ties the result to cited evidence. It
            covers the familiar insurance questions, plus the agent-specific risks traditional
            underwriting misses: autonomy, prompt injection, memory leakage, tool chains,
            multi-agent propagation, and silent model change.
          </p>
          <div className="score-metrics" aria-label="OllyUW scoring model summary">
            <div>
              <strong>12</strong>
              <span>risk dimensions</span>
            </div>
            <div>
              <strong>0-10</strong>
              <span>per-dimension score</span>
            </div>
            <div>
              <strong>Cited</strong>
              <span>source-backed findings</span>
            </div>
          </div>
          <Link className="text-link-button" to="/scoring">Read more</Link>
        </div>

        <div className="radar-panel" aria-label="Sample 12 dimension risk scores">
          <RadarChart />
        </div>
      </div>
    </section>
  )
}
