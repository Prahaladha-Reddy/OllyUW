import { Trash2 } from "lucide-react";
import { useState } from "react";
import { NewConversationModal } from "../components/workspace/NewConversationModal.jsx";
import { NewProjectModal } from "../components/workspace/NewProjectModal.jsx";
import { ProjectCard } from "../components/workspace/ProjectCard.jsx";
import { WorkspaceLayout } from "../components/workspace/WorkspaceLayout.jsx";
import { createConversation, createProject, deleteProject } from "../lib/api.js";
import { useWorkspace } from "../hooks/useWorkspace.js";

export function ProjectsDashboard({ onNavigate, session }) {
  const workspace = useWorkspace(session);
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [conversationProject, setConversationProject] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState("");

  async function handleCreateProject(payload) {
    setIsSubmitting(true);
    setActionError("");

    try {
      const project = await createProject(session, payload);
      await workspace.refresh();
      setProjectModalOpen(false);
      onNavigate("projectDetail", { projectId: project.id || project.project_id });
    } catch (error) {
      setActionError(error.message || "Could not create project.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCreateConversation(payload) {
    if (!conversationProject) {
      return;
    }

    setIsSubmitting(true);
    setActionError("");

    try {
      const conversation = await createConversation(session, conversationProject.id, payload);
      await workspace.refresh();
      setConversationProject(null);
      onNavigate("conversation", {
        conversationId: conversation.id || conversation.conversation_id,
        projectId: conversationProject.id,
      });
    } catch (error) {
      setActionError(error.message || "Could not create conversation.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteProject(project) {
    const confirmed = window.confirm(`Delete "${project.name}" and its files?`);
    if (!confirmed) {
      return;
    }

    setActionError("");
    try {
      await deleteProject(session, project.id);
      await workspace.refresh();
    } catch (error) {
      setActionError(error.message || "Could not delete project.");
    }
  }

  return (
    <>
      <WorkspaceLayout
        onCreateConversation={setConversationProject}
        onCreateProject={() => setProjectModalOpen(true)}
        onNavigate={onNavigate}
        projectDetails={workspace.projectDetails}
        projects={workspace.projects}
      >
        <div className="workspace-header">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1>Projects</h1>
            <p>Keep each underwriting review, evidence package, and conversation in one place.</p>
          </div>
        </div>

        {actionError && <p className="workspace-alert">{actionError}</p>}
        {workspace.error && <p className="workspace-alert">{workspace.error}</p>}

        {workspace.isLoading && <WorkspaceState title="Loading projects" copy="Fetching your workspace." />}

        {!workspace.isLoading && !workspace.hasProjects && (
          <div className="empty-panel empty-panel-large">
            <h3>Create your first project</h3>
            <p>Start with the company or submission package you want OllyUW to review.</p>
            <button className="dark-button" type="button" onClick={() => setProjectModalOpen(true)}>
              Create project
            </button>
          </div>
        )}

        {!workspace.isLoading && workspace.hasProjects && (
          <div className="project-grid">
            {workspace.projects.map((project) => (
              <div className="project-card-shell" key={project.id}>
                <ProjectCard project={project} onNavigate={onNavigate} />
                <button className="icon-text-button project-delete-button" type="button" onClick={() => handleDeleteProject(project)}>
                  <Trash2 size={16} />
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </WorkspaceLayout>

      {projectModalOpen && (
        <NewProjectModal
          existingProjects={workspace.projects}
          isSubmitting={isSubmitting}
          onClose={() => setProjectModalOpen(false)}
          onSubmit={handleCreateProject}
          serverError={actionError}
        />
      )}
      {conversationProject && (
        <NewConversationModal
          isSubmitting={isSubmitting}
          onClose={() => setConversationProject(null)}
          onSubmit={handleCreateConversation}
          project={conversationProject}
          serverError={actionError}
        />
      )}
    </>
  );
}

function WorkspaceState({ copy, title }) {
  return (
    <div className="state-panel">
      <h2>{title}</h2>
      <p>{copy}</p>
    </div>
  );
}
