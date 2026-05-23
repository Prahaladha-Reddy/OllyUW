import { ArrowLeft, MessageSquare, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { NavButton } from "../components/navigation/NavButton.jsx";
import { ConversationList } from "../components/workspace/ConversationList.jsx";
import { FileList } from "../components/workspace/FileList.jsx";
import { NewConversationModal } from "../components/workspace/NewConversationModal.jsx";
import { NewProjectModal } from "../components/workspace/NewProjectModal.jsx";
import { UploadArea } from "../components/workspace/UploadArea.jsx";
import { WorkspaceLayout } from "../components/workspace/WorkspaceLayout.jsx";
import {
  createConversation,
  createProject,
  deleteConversation,
  deleteProject,
  deleteProjectFile,
  uploadProjectFiles,
} from "../lib/api.js";
import { useWorkspace } from "../hooks/useWorkspace.js";
import { formatDate } from "../utils/format.js";

export function ProjectDetail({ onNavigate, projectId, session }) {
  const workspace = useWorkspace(session);
  const project = workspace.projectDetails[projectId] || workspace.projects.find((item) => item.id === projectId);
  const files = project?.files || [];
  const conversations = project?.conversations || [];
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [conversationProject, setConversationProject] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  async function handleCreateProject(payload) {
    setIsSubmitting(true);
    setActionError("");

    try {
      const created = await createProject(session, payload);
      await workspace.refresh();
      setProjectModalOpen(false);
      onNavigate("projectDetail", { projectId: created.id || created.project_id });
    } catch (error) {
      setActionError(error.message || "Could not create project.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCreateConversation(payload) {
    const targetProject = conversationProject || project;
    if (!targetProject) {
      return;
    }

    setIsSubmitting(true);
    setActionError("");

    try {
      const created = await createConversation(session, targetProject.id, payload);
      await workspace.refresh();
      setConversationProject(null);
      onNavigate("conversation", {
        conversationId: created.id || created.conversation_id,
        projectId: targetProject.id,
      });
    } catch (error) {
      setActionError(error.message || "Could not create conversation.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleUpload(filesToUpload) {
    setIsUploading(true);
    setActionError("");
    setActionMessage("");

    try {
      await uploadProjectFiles(session, projectId, filesToUpload);
      await workspace.refresh();
      setActionMessage(`${filesToUpload.length} file${filesToUpload.length === 1 ? "" : "s"} uploaded.`);
    } catch (error) {
      setActionError(error.message || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDeleteFile(file) {
    const confirmed = window.confirm(`Delete "${file.original_name}"?`);
    if (!confirmed) {
      return;
    }

    setActionError("");
    try {
      await deleteProjectFile(session, projectId, file.id);
      await workspace.refresh();
    } catch (error) {
      setActionError(error.message || "Could not delete file.");
    }
  }

  async function handleDeleteConversation(conversation) {
    const confirmed = window.confirm(`Delete "${conversation.title}"?`);
    if (!confirmed) {
      return;
    }

    setActionError("");
    try {
      await deleteConversation(session, projectId, conversation.id);
      await workspace.refresh();
    } catch (error) {
      setActionError(error.message || "Could not delete conversation.");
    }
  }

  async function handleDeleteProject() {
    if (!project) {
      return;
    }

    const confirmed = window.confirm(`Delete "${project.name}" and all files?`);
    if (!confirmed) {
      return;
    }

    setActionError("");
    try {
      await deleteProject(session, projectId);
      onNavigate("projects", {}, { replace: true });
    } catch (error) {
      setActionError(error.message || "Could not delete project.");
    }
  }

  const loadingProject = workspace.isLoading && !project;

  return (
    <>
      <WorkspaceLayout
        activeProjectId={projectId}
        onCreateConversation={setConversationProject}
        onCreateProject={() => setProjectModalOpen(true)}
        onNavigate={onNavigate}
        projectDetails={workspace.projectDetails}
        projects={workspace.projects}
      >
        {loadingProject && <WorkspaceState title="Loading project" copy="Opening the underwriting file." />}

        {!loadingProject && !project && (
          <div className="state-panel">
            <h2>Project not found</h2>
            <p>This project may have been deleted or you may not have access.</p>
            <NavButton className="dark-button" route="projects" onNavigate={onNavigate}>
              Back to Projects
            </NavButton>
          </div>
        )}

        {project && (
          <>
            <div className="workspace-header">
              <div>
                <p className="eyebrow">Project</p>
                <h1>{project.name}</h1>
                <p>
                  {project.description || "Upload source documents, create conversations, and keep every answer tied to this project."}
                </p>
                <span className="workspace-submeta">Created {formatDate(project.created_at)}</span>
              </div>
              <div className="workspace-actions">
                <button className="dark-button" type="button" onClick={() => setConversationProject(project)}>
                  <MessageSquare size={18} />
                  New Conversation
                </button>
                <button className="icon-text-button danger-button" type="button" onClick={handleDeleteProject}>
                  <Trash2 size={16} />
                  Delete Project
                </button>
              </div>
            </div>

            {actionError && <p className="workspace-alert">{actionError}</p>}
            {workspace.error && <p className="workspace-alert">{workspace.error}</p>}
            {actionMessage && <p className="workspace-success">{actionMessage}</p>}

            <section className="workspace-section">
              <div className="workspace-section-heading">
                <div>
                  <h2>Upload files</h2>
                  <p>Add PDFs, docs, spreadsheets, configs, logs, and other evidence to this project.</p>
                </div>
              </div>
              <UploadArea disabled={isUploading} onUpload={handleUpload} />
              {isUploading && <p className="workspace-note">Uploading and preparing files...</p>}
            </section>

            <section className="workspace-section">
              <div className="workspace-section-heading">
                <div>
                  <h2>Files in project</h2>
                  <p>{files.length} source file{files.length === 1 ? "" : "s"} available to conversations.</p>
                </div>
              </div>
              <FileList files={files} onDeleteFile={handleDeleteFile} />
            </section>

            <section className="workspace-section">
              <div className="workspace-section-heading">
                <div>
                  <h2>Conversations</h2>
                  <p>Ask separate underwriting questions without losing the project evidence context.</p>
                </div>
                <button className="pill-button" type="button" onClick={() => setConversationProject(project)}>
                  <Plus size={18} />
                  New Conversation
                </button>
              </div>
              <ConversationList
                conversations={conversations}
                onDeleteConversation={handleDeleteConversation}
                onNavigate={onNavigate}
                projectId={projectId}
              />
            </section>

            <NavButton className="workspace-back-link" route="projects" onNavigate={onNavigate}>
              <ArrowLeft size={17} />
              Back to Projects
            </NavButton>
          </>
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
