import { Sidebar } from "./Sidebar.jsx";

export function WorkspaceLayout({
  activeConversationId,
  activeProjectId,
  children,
  onCreateConversation,
  onCreateProject,
  onNavigate,
  projects,
  projectDetails,
}) {
  return (
    <section className="workspace-page">
      <Sidebar
        activeConversationId={activeConversationId}
        activeProjectId={activeProjectId}
        onCreateConversation={onCreateConversation}
        onCreateProject={onCreateProject}
        onNavigate={onNavigate}
        projects={projects}
        projectDetails={projectDetails}
      />
      <div className="workspace-main">{children}</div>
    </section>
  );
}
