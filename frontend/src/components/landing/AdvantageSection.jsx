export function AdvantageSection() {
  return (
    <section className="advantage-section section-dark">
      <div className="section-heading">
        <h2>Move from intake to defensible underwriting faster.</h2>
        <p>
          The agent does not stop at document upload. It builds the underwriting file, drafts the
          memo, and stays available to answer follow-up questions from the same grounded evidence.
        </p>
      </div>
      <div className="advantage-grid">
        <article>
          <span>Evidence</span>
          <h3>Turn messy files into an underwriting record.</h3>
          <p>
            Security reports, contracts, policies, architecture diagrams, control logs, and incident
            notes become structured evidence that can be searched, cited, and reviewed.
          </p>
        </article>
        <article>
          <span>Judgment</span>
          <h3>Translate technical controls into insurance judgment.</h3>
          <p>
            Unauthorized actions, data exposure, output reliability, bias, drift, operational
            control, and loss severity roll into terms an underwriter can actually use.
          </p>
        </article>
        <article>
          <span>Chat</span>
          <h3>Question the file after the memo is written.</h3>
          <p>
            Ask what supports a finding, where a contradiction came from, or which evidence would
            improve the quote. OllyUW answers from the source documents.
          </p>
        </article>
      </div>
    </section>
  );
}
