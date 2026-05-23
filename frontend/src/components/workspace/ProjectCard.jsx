import { NavButton } from "../navigation/NavButton.jsx";
import { formatDate } from "../../utils/format.js";

export function ProjectCard({ onNavigate, project }) {
  return (
    <NavButton
      className="project-card"
      route="projectDetail"
      params={{ projectId: project.id }}
      onNavigate={onNavigate}
    >
      <span>Project</span>
      <h3>{project.name}</h3>
      {project.description && <p>{project.description}</p>}
      <div className="project-card-meta">
        <strong>{project.file_count} files</strong>
        <strong>{project.conversation_count} conv.</strong>
      </div>
      <time>{formatDate(project.created_at)}</time>
    </NavButton>
  );
}
