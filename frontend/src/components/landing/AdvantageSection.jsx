export function AdvantageSection() {
  return (
    <section className="advantage-section section-dark">
      <div className="section-heading">
        <h2>Built around persistence, not prompt gymnastics.</h2>
        <p>
          The useful part is not just model output. It is the durable machine state around the
          model: folders, browser sessions, connectors, task history, and the ability to resume.
        </p>
      </div>
      <div className="advantage-grid">
        <article>
          <span>Files</span>
          <h3>Keep a real working file system.</h3>
          <p>
            Upload folders, preserve structure, and give the agent a stable place to read, write,
            organize, and hand work back to you.
          </p>
        </article>
        <article>
          <span>Sessions</span>
          <h3>Reuse app logins and browser state.</h3>
          <p>
            The computer keeps the state that matters: cookies, credentials, bookmarks, local
            storage, and enough context to continue the same task later.
          </p>
        </article>
        <article>
          <span>Control</span>
          <h3>See what the agent is doing.</h3>
          <p>
            Tasks, outputs, and connected systems are visible from one shell so the product feels
            like operating a machine, not hoping a chat history is enough.
          </p>
        </article>
      </div>
    </section>
  );
}
