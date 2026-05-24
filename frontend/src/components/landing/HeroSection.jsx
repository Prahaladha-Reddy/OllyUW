import { Link } from 'react-router-dom'

export function HeroSection() {
  return (
    <section className="hero section-dark">
      <div className="hero-inner">
        <p className="eyebrow">AI Underwriting Agent</p>
        <h1>Evidence-grounded underwriting for AI agents.</h1>
        <p className="hero-copy">
          Traditional underwriting loses days to document review, follow-up requests, and manual
          cross-checking. OllyUW reads the evidence package, finds contradictions, scores the 12 AI
          liability dimensions, drafts the memo, and keeps answering from the cited source file.
        </p>
        <Link className="pill-button hero-button" to="/review">
          Start review
        </Link>
      </div>

      <div className="hero-preview" aria-label="Underwriting memo preview">
        <div className="memo-shell">
          <div className="memo-topline">
            <span>AI Agent Review</span>
            <strong>Risk 87</strong>
          </div>
          <div className="memo-grid">
            <span>CR-02</span>
            <p>Privacy commitments conflict with storage, retention, and tenant-isolation evidence.</p>
          </div>
          <div className="memo-grid">
            <span>Ask</span>
            <p>Why is D3 high? OllyUW cites the tool schema, HITL log, and missing kill-switch proof.</p>
          </div>
        </div>
      </div>
    </section>
  )
}
