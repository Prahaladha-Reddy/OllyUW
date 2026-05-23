import { workflowSteps } from "../../data/landingContent.js";
import { NavButton } from "../navigation/NavButton.jsx";

export function WorkflowSection({ onNavigate }) {
  return (
    <section className="workflow-section section-light">
      <div className="workflow-copy">
        <p className="eyebrow">Workflow</p>
        <h2>From scattered evidence to a living underwriting file.</h2>
      </div>
      <div className="workflow-list">
        {workflowSteps.map((step, index) => (
          <div key={step}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <p>{step}</p>
          </div>
        ))}
      </div>
      <NavButton className="dark-button" route="auth" onNavigate={onNavigate}>
        Start review
      </NavButton>
    </section>
  );
}
