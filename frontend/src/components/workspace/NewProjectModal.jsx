import { useState } from "react";
import { Modal } from "./Modal.jsx";

export function NewProjectModal({ existingProjects, isSubmitting, onClose, onSubmit, serverError }) {
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "").trim();
    const description = String(form.get("description") || "").trim();

    if (name.length < 3) {
      setError("Project name must be at least 3 characters.");
      return;
    }

    if (existingProjects.some((project) => project.name.toLowerCase() === name.toLowerCase())) {
      setError("A project with this name already exists.");
      return;
    }

    setError("");
    onSubmit({ name, description: description || null });
  }

  return (
    <Modal title="Create New Project" onClose={onClose}>
      <form className="modal-form" onSubmit={handleSubmit}>
        <label htmlFor="project-name">Project Name</label>
        <input id="project-name" name="name" maxLength={100} placeholder="Company A Underwriting" required />

        <label htmlFor="project-description">Description</label>
        <textarea
          id="project-description"
          name="description"
          maxLength={500}
          placeholder="Optional notes about this underwriting review"
          rows={4}
        />

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
