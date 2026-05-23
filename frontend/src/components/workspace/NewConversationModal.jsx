import { useState } from "react";
import { Modal } from "./Modal.jsx";

export function NewConversationModal({ isSubmitting, onClose, onSubmit, project, serverError }) {
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") || "").trim();

    if (title.length < 3) {
      setError("Conversation title must be at least 3 characters.");
      return;
    }

    setError("");
    onSubmit({ title });
  }

  return (
    <Modal title="Start New Conversation" onClose={onClose}>
      <form className="modal-form" onSubmit={handleSubmit}>
        <p className="modal-context">{project?.name}</p>
        <label htmlFor="conversation-title">Conversation Title</label>
        <input id="conversation-title" name="title" maxLength={100} placeholder="Liability Analysis" required />

        {(error || serverError) && <p className="modal-error">{error || serverError}</p>}

        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="pill-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
