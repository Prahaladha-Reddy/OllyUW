import { comparisonRows } from "../../data/landingContent.js";

export function ManualComparisonSection() {
  return (
    <section className="question-section section-light">
      <div className="section-heading">
        <h2>Manual underwriting versus OllyUW.</h2>
        <p>
          Traditional underwriting is slow because the evidence is scattered and every conclusion
          has to be rebuilt by hand. OllyUW keeps the same underwriting discipline, but makes the
          evidence, reasoning, and follow-up questions traceable from the start.
        </p>
      </div>

      <div className="uw-comparison" aria-label="Manual underwriting compared with OllyUW">
        <div className="comparison-title-row">
          <div className="lane-title lane-manual">
            <span>Manual underwriting</span>
            <strong>Days of review</strong>
          </div>
          <div className="lane-title lane-olly">
            <span>With OllyUW</span>
            <strong>Grounded review in minutes</strong>
          </div>
        </div>

        <div className="comparison-flow">
          {comparisonRows.map((row, index) => (
            <div className="comparison-row" key={row.step}>
              <div className="lane-copy lane-copy-manual">
                <p>{row.manual}</p>
              </div>
              <div className="comparison-step">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{row.step}</strong>
              </div>
              <div className="lane-copy lane-copy-olly">
                <p>{row.olly}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="comparison-result">
          <span>Result</span>
          <p>
            The underwriter still makes the decision. OllyUW makes the file faster to understand,
            easier to defend, and ready for grounded follow-up instead of another manual search.
          </p>
        </div>
      </div>
    </section>
  );
}
