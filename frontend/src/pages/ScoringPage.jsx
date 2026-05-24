import { evidenceDocumentExamples } from '../data/landingContent'
import { riskDimensions } from '../data/riskDimensions'

export function ScoringPage() {
  return (
    <section className="page scoring-page section-light" aria-label="OllyUW scoring explainer">
      <div className="scoring-hero">
        <p className="eyebrow">Scoring Model</p>
        <h1>How OllyUW scores AI agent liability.</h1>
        <p>
          OllyUW does not need a perfect submission package to start. It reads the evidence that is
          available, marks what is missing, and scores each dimension with citations so the
          underwriter can see what the model relied on.
        </p>
      </div>

      <div className="scoring-overview">
        <article>
          <span>Why score</span>
          <p>
            AI agent risk is not one question. A safe-looking system can still leak data, drift after
            underwriting, call unsafe tools, or fail when hostile content enters the context. The 12
            dimensions keep those risks separate before they become one underwriting position.
          </p>
        </article>
        <article>
          <span>How scores work</span>
          <p>
            Each dimension is scored from 0 to 10. A higher score means higher underwriting concern.
            Strong controls, tested evidence, and clean operating history lower the score. Missing,
            conflicting, or weak evidence raises uncertainty.
          </p>
        </article>
        <article>
          <span>Missing evidence</span>
          <p>
            Vendors may not submit every artifact because it is unavailable, private, customer-owned,
            or not yet produced. OllyUW scores from what is available and turns gaps into clear
            subjectivities or follow-up requests.
          </p>
        </article>
      </div>

      <div className="document-section">
        <div>
          <p className="eyebrow">Evidence OllyUW Can Use</p>
          <h2>Useful documents, not mandatory documents.</h2>
        </div>
        <div className="document-list">
          {evidenceDocumentExamples.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
      </div>

      <div className="dimension-explainer">
        {riskDimensions.map((dimension) => (
          <article key={dimension.code}>
            <div>
              <span>{dimension.code}</span>
              <strong>{dimension.label}</strong>
            </div>
            <h3>{dimension.title}</h3>
            <p>{dimension.detail}</p>
            <ul>
              {dimension.evidence.map((source) => (
                <li key={source}>{source}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  )
}
