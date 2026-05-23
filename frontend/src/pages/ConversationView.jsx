import { ArrowLeft, Plus } from "lucide-react";
import { useCallback, useState } from "react";
import { NavButton } from "../components/navigation/NavButton.jsx";
import { NewConversationModal } from "../components/workspace/NewConversationModal.jsx";
import { NewProjectModal } from "../components/workspace/NewProjectModal.jsx";
import { MessageInput } from "../components/workspace/MessageInput.jsx";
import { MessageList } from "../components/workspace/MessageList.jsx";
import { UploadArea } from "../components/workspace/UploadArea.jsx";
import { WorkspaceLayout } from "../components/workspace/WorkspaceLayout.jsx";
import {
  createConversation,
  createProject,
  sendConversationMessage,
  streamConversation,
  uploadConversationFiles,
} from "../lib/api.js";
import { useConversation } from "../hooks/useConversation.js";
import { useWorkspace } from "../hooks/useWorkspace.js";

export function ConversationView({ conversationId, onNavigate, projectId, session }) {
  const workspace = useWorkspace(session);
  const { conversation, messages, error: conversationError, isLoading, refresh } = useConversation(
    session,
    projectId,
    conversationId,
  );
  const project = workspace.projectDetails[projectId] || workspace.projects.find((item) => item.id === projectId);

  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [conversationProject, setConversationProject] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
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
    if (!targetProject) return;

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
      // Use conversation-scoped upload so files are pushed to the live sandbox
      await uploadConversationFiles(session, projectId, conversationId, filesToUpload);
      await workspace.refresh();
      setActionMessage(`${filesToUpload.length} file${filesToUpload.length === 1 ? "" : "s"} added.`);
    } catch (error) {
      setActionError(error.message || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  const handleSend = useCallback(
    async (text) => {
      setIsSending(true);
      setStreamingText("");
      setActionError("");

      try {
        // 1. Persist user message and enqueue to agent
        await sendConversationMessage(session, projectId, conversationId, text);

        // Optimistically refresh so user message shows immediately
        await refresh();

        // 2. Open SSE stream and accumulate agent response
        let finalReceived = false;
        for await (const event of streamConversation(session, projectId, conversationId)) {
          if (event.type === "model_delta") {
            setStreamingText((prev) => prev + (event.text || ""));
          } else if (event.type === "final") {
            finalReceived = true;
            setStreamingText("");
            // Reload from DB — agent's final answer is now persisted
            await refresh();
            break;
          } else if (event.type === "sse_heartbeat" || event.type === "stream_connected") {
            // no-op
          }
        }

        // Fallback: if stream closed without a final event
        if (!finalReceived) {
          setStreamingText("");
          await refresh();
        }
      } catch (error) {
        setActionError(error.message || "Could not send message.");
        setStreamingText("");
      } finally {
        setIsSending(false);
      }
    },
    [session, projectId, conversationId, refresh],
  );

  return (
    <>
      <WorkspaceLayout
        activeConversationId={conversationId}
        activeProjectId={projectId}
        onCreateConversation={setConversationProject}
        onCreateProject={() => setProjectModalOpen(true)}
        onNavigate={onNavigate}
        projectDetails={workspace.projectDetails}
        projects={workspace.projects}
      >
        <div className="workspace-header conversation-header">
          <div>
            <p className="eyebrow">{project?.name ? `Projects / ${project.name}` : "Conversation"}</p>
            <h1>{conversation?.title || "Conversation"}</h1>
            <p>Ask questions against the uploaded evidence. Answers stay attached to this project record.</p>
          </div>
          <button className="pill-button" type="button" onClick={() => setConversationProject(project)}>
            <Plus size={18} />
            New Conversation
          </button>
        </div>

        {actionError && <p className="workspace-alert">{actionError}</p>}
        {workspace.error && <p className="workspace-alert">{workspace.error}</p>}
        {conversationError && <p className="workspace-alert">{conversationError}</p>}
        {actionMessage && <p className="workspace-success">{actionMessage}</p>}

        {isLoading && (
          <div className="state-panel">
            <h2>Loading conversation</h2>
            <p>Opening the message history.</p>
          </div>
        )}

        {!isLoading && (
          <section className="workspace-section conversation-panel">
            <div className="workspace-section-heading">
              <div>
                <h2>Messages</h2>
                <p>{messages.length ? `${messages.length} messages` : "No messages yet"}</p>
              </div>
            </div>
            <MessageList messages={messages} streamingText={streamingText} />
            <MessageInput disabled={isSending || !conversation} onSend={handleSend} />
            {isSending && !streamingText && <p className="workspace-note">Agent is thinking...</p>}
          </section>
        )}

        <section className="workspace-section">
          <div className="workspace-section-heading">
            <div>
              <h2>Add files</h2>
              <p>Files added here are available to this conversation immediately.</p>
            </div>
          </div>
          <UploadArea disabled={isUploading} onUpload={handleUpload} />
        </section>

        <NavButton className="workspace-back-link" route="projectDetail" params={{ projectId }} onNavigate={onNavigate}>
          <ArrowLeft size={17} />
          Back to Project
        </NavButton>
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
