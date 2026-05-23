import { Send } from "lucide-react";
import { useState } from "react";

export function MessageInput({ disabled, onSend }) {
  const [text, setText] = useState("");

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) {
      return;
    }
    onSend(trimmed);
    setText("");
  }

  return (
    <div className="message-input">
      <textarea
        value={text}
        placeholder="Ask a question about the documents"
        disabled={disabled}
        rows={2}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <button className="pill-button" type="button" disabled={disabled || !text.trim()} onClick={submit}>
        <Send size={16} />
        Send
      </button>
    </div>
  );
}
