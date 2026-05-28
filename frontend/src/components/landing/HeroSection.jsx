import { Link } from 'react-router-dom'

export function HeroSection() {
  return (
    <section className="hero section-dark">
      <div className="hero-inner">
        <p className="eyebrow">Your AI's Computer</p>
        <h1>A persistent cloud computer your AI can actually operate.</h1>
        <p className="hero-copy">
          Most agents forget everything between chats or drop you into a raw sandbox with no real
          operating surface. Olly gives the model one durable computer with files, app sessions,
          memory, and a visible workspace you can come back to.
        </p>
        <Link className="pill-button hero-button" to="/review">
          Unlock your computer
        </Link>
      </div>

      <div className="hero-preview" aria-label="Second computer preview">
        <div className="memo-shell">
          <div className="memo-topline">
            <span>Computer Online</span>
            <strong>3 apps</strong>
          </div>
          <div className="memo-grid">
            <span>Files</span>
            <p>Research, drafts, and uploaded folders stay in place instead of disappearing between sessions.</p>
          </div>
          <div className="memo-grid">
            <span>Apps</span>
            <p>Signed-in sessions and saved context let the agent continue work without starting over.</p>
          </div>
        </div>
      </div>
    </section>
  )
}
