import { formatDateTime } from "../../utils/format.js";

export function MessageList({ messages, streamingText = "" }) {
  const hasContent = messages.length > 0 || streamingText;

  if (!hasContent) {
    return (
      <div className="empty-panel message-empty">
        <h3>Ask a question to get started</h3>
        <p>Ask about risk, exclusions, missing evidence, or how a document supports the underwriting position.</p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <article className={`message-bubble is-${message.role}`} key={message.id}>
          <span>{message.role === "assistant" ? "OllyUW" : "You"}</span>
          <p>{message.content}</p>
          {message.citations?.length > 0 && (
            <div className="citation-row">
              {message.citations.map((citation) => (
                <strong key={`${citation.filename}-${citation.storage_path}`}>{citation.filename}</strong>
              ))}
            </div>
          )}
          <time>{formatDateTime(message.created_at)}</time>
        </article>
      ))}

      {streamingText && (
        <article className="message-bubble is-assistant is-streaming">
          <span>OllyUW</span>
          <p>{streamingText}</p>
        </article>
      )}
    </div>
  );
}
