import { useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { Plus, FileText, Settings, Folder, ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useProjects, useProject, useCreateProject } from '../../hooks/queries'
import { NewProjectModal } from './NewProjectModal'

export function Sidebar() {
  const { signOut, user } = useAuth()
  const navigate = useNavigate()
  const { projectId: activeProjectId, conversationId: activeConversationId } = useParams()
  const { data: projects = [] } = useProjects()
  const { data: activeProject } = useProject(activeProjectId ?? null)
  const recentConversations = activeProject?.conversations ?? []

  const [showNewProject, setShowNewProject] = useState(false)
  const createProject = useCreateProject()

  const rawName = user?.user_metadata?.full_name ?? user?.email?.split('@')[0] ?? 'User'
  const displayName = rawName.replace(/[._]/g, ' ')
  const initials = displayName[0]?.toUpperCase() ?? '?'

  async function handleCreateProject({ name, description }) {
    const result = await createProject.mutateAsync({ name, description })
    const id = result.id ?? result.project_id
    setShowNewProject(false)
    navigate(`/projects/${id}`)
  }

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  return (
    <>
      <aside className="ws-sidebar">
        <div className="ws-sidebar-header">
          <Link to="/" className="ws-sidebar-brand">OllyUW</Link>
        </div>

        <div className="ws-sidebar-actions">
          <button className="ws-new-project-btn" type="button" onClick={() => setShowNewProject(true)}>
            <Plus size={14} />
            New project
          </button>
        </div>

        <nav className="ws-sidebar-nav">
          <div className="ws-nav-section">
            <span className="ws-nav-section-label">Projects</span>
            {projects.map((project) => (
              <button
                key={project.id}
                className={`ws-project-item ${project.id === activeProjectId ? 'is-active' : ''}`}
                type="button"
                onClick={() => navigate(`/projects/${project.id}`)}
              >
                <Folder size={13} className="ws-project-icon" />
                <span className="ws-project-name" title={project.name}>{project.name}</span>
              </button>
            ))}
          </div>

          {activeProject && (
            <div className="ws-nav-section">
              <span className="ws-nav-section-label" title={activeProject.name}>
                {activeProject.name}
              </span>
              {recentConversations.length === 0 ? (
                <span className="ws-nav-empty">No conversations yet</span>
              ) : (
                recentConversations.slice(0, 8).map((conv) => (
                  <Link
                    key={conv.id}
                    to={`/projects/${activeProjectId}/conversations/${conv.id}`}
                    className={`ws-conv-item ${conv.id === activeConversationId ? 'is-active' : ''}`}
                  >
                    <FileText size={12} className="ws-conv-icon" />
                    <span className="ws-conv-name" title={conv.title}>{conv.title}</span>
                  </Link>
                ))
              )}
            </div>
          )}
        </nav>

        <div className="ws-sidebar-footer">
          <div className="ws-user-row">
            <div className="ws-user-avatar">{initials}</div>
            <div className="ws-user-meta">
              <span className="ws-user-name">{displayName}</span>
              <span className="ws-user-email-text">{user?.email}</span>
            </div>
            <ChevronDown size={13} className="ws-user-chevron" />
          </div>
          <div className="ws-footer-actions">
            <button className="ws-settings-btn" type="button" title="Sign out" onClick={handleSignOut}>
              <Settings size={13} />
            </button>
          </div>
        </div>
      </aside>

      {showNewProject && (
        <NewProjectModal
          onConfirm={handleCreateProject}
          onCancel={() => setShowNewProject(false)}
          loading={createProject.isPending}
        />
      )}
    </>
  )
}
