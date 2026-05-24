import { Link } from 'react-router-dom'
import { workflowSteps } from '../../data/landingContent'

export function WorkflowSection() {
  return (
    <section className="workflow-section section-light">
      <div className="workflow-copy">
        <p className="eyebrow">Workflow</p>
        <h2>From scattered evidence to a living underwriting file.</h2>
      </div>
      <div className="workflow-list">
        {workflowSteps.map((step, index) => (
          <div key={step}>
            <span>{String(index + 1).padStart(2, '0')}</span>
            <p>{step}</p>
          </div>
        ))}
      </div>
      <Link className="dark-button" to="/review">Start review</Link>
    </section>
  )
}
