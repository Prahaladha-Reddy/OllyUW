import { ChevronDown, ChevronRight, FileText, FolderOpen, MessageSquare, Plus } from "lucide-react";
import { useState } from "react";
import { NavButton } from "../navigation/NavButton.jsx";

export function Sidebar({
  activeConversationId,
  activeProjectId,
  onCreateConversation,
  onCreateProject,
  onNavigate,
  projects,
  projectDetails,
}) {
  const [openFileProjects, setOpenFileProjects] = useState({});
  const [openProjectItems, setOpenProjectItems] = useState({});

  function toggleFileProject(projectId) {
    setOpenFileProjects((current) => ({ ...current, [projectId]: !current[projectId] }));
  }

  function toggleProjectItem(projectId) {
    setOpenProjectItems((current) => ({ ...current, [projectId]: !current[projectId] }));
  }

  return (
    <aside className="workspace-sidebar" aria-label="Workspace navigation">
      <SidebarSection title="Files">
        {projects.length === 0 ? (
          <p className="sidebar-empty">No files yet</p>
        ) : (
          projects.map((project) => {
            const detail = projectDetails[project.id];
            const files = detail?.files || [];
            const isOpen = openFileProjects[project.id] ?? project.id === activeProjectId;

            return (
              <div className="sidebar-group" key={project.id}>
                <button className="sidebar-row" type="button" onClick={() => toggleFileProject(project.id)}>
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span>{project.name}</span>
                </button>
                {isOpen && (
                  <div className="sidebar-nested">
                    {files.length === 0 ? (
                      <p className="sidebar-empty">No files yet</p>
                    ) : (
                      files.map((file) => (
                        <span className="sidebar-leaf" key={file.id}>
                          <FileText size={14} />
                          {file.original_name}
                        </span>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </SidebarSection>

      <SidebarSection title="Projects">
        {projects.length === 0 ? (
          <p className="sidebar-empty">No projects yet</p>
        ) : (
          projects.map((project) => {
            const detail = projectDetails[project.id];
            const conversations = detail?.conversations || [];
            const isOpen = openProjectItems[project.id] ?? project.id === activeProjectId;
            const isActiveProject = project.id === activeProjectId;

            return (
              <div className={`sidebar-group ${isActiveProject ? "is-active" : ""}`} key={project.id}>
                <button className="sidebar-row" type="button" onClick={() => toggleProjectItem(project.id)}>
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span>{project.name}</span>
                </button>
                {isOpen && (
                  <div className="sidebar-nested">
                    <NavButton
                      className="sidebar-leaf"
                      route="projectDetail"
                      params={{ projectId: project.id }}
                      onNavigate={onNavigate}
                    >
                      <FolderOpen size={14} />
                      Files ({project.file_count ?? detail?.files?.length ?? 0})
                    </NavButton>
                    <span className="sidebar-leaf">
                      <MessageSquare size={14} />
                      Conversations ({project.conversation_count ?? conversations.length})
                    </span>
                    {conversations.map((conversation) => (
                      <NavButton
                        className={`sidebar-leaf sidebar-conversation ${
                          conversation.id === activeConversationId ? "is-active" : ""
                        }`}
                        route="conversation"
                        params={{ projectId: project.id, conversationId: conversation.id }}
                        onNavigate={onNavigate}
                        key={conversation.id}
                      >
                        {conversation.title}
                      </NavButton>
                    ))}
                    <button
                      className="sidebar-action"
                      type="button"
                      onClick={() => onCreateConversation(project)}
                    >
                      <Plus size={14} />
                      New Conversation
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
        <button className="sidebar-new-project" type="button" onClick={onCreateProject}>
          <Plus size={15} />
          New Project
        </button>
      </SidebarSection>
    </aside>
  );
}

function SidebarSection({ children, title }) {
  return (
    <section className="sidebar-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
