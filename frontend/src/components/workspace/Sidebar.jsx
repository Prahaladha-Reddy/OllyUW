import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ChevronRight, FileText, MessageSquare, Plus, LogOut, Loader2, FolderOpen } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useProjects, useProject, useCreateProject, useCreateConversation } from '../../hooks/queries'
import { NewProjectModal } from './NewProjectModal'
import { NewConversationModal } from './NewConversationModal'

export function Sidebar() {
  const { signOut, user } = useAuth()
  const navigate = useNavigate()
  const { projectId: activeProjectId, conversationId: activeConversationId } = useParams()
  const { data: projects = [], isLoading } = useProjects()

  // Separate expand state for FILES and PROJECTS sections
  const [filesOpen, setFilesOpen] = useState({})
  const [projectsOpen, setProjectsOpen] = useState({})
  const [showNewProject, setShowNewProject] = useState(false)
  const [newConvProjectId, setNewConvProjectId] = useState(null)

  const createProject = useCreateProject()
  const createConversation = useCreateConversation(newConvProjectId)

  // Auto-expand active project in both sections
  useEffect(() => {
    if (activeProjectId) {
      setFilesOpen((prev) => ({ ...prev, [activeProjectId]: true }))
      setProjectsOpen((prev) => ({ ...prev, [activeProjectId]: true }))
    }
  }, [activeProjectId])

  async function handleCreateProject({ name, description }) {
    const result = await createProject.mutateAsync({ name, description })
    const id = result.id ?? result.project_id
    setShowNewProject(false)
    navigate(`/projects/${id}`)
  }

  async function handleCreateConversation({ title }) {
    const result = await createConversation.mutateAsync({ title })
    const id = result.id ?? result.conversation_id
    setNewConvProjectId(null)
    navigate(`/projects/${newConvProjectId}/conversations/${id}`)
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
          <button className="ws-sidebar-btn" type="button" onClick={() => setShowNewProject(true)}>
            <Plus size={13} />
            New project
          </button>
        </div>

        <nav className="ws-sidebar-nav">
          {isLoading && (
            <div className="ws-sidebar-status">
              <Loader2 size={13} className="spin" /> Loading…
            </div>
          )}

          {/* ── FILES section ── */}
          <div className="ws-nav-section">
            <span className="ws-nav-section-label">Files</span>
            {projects.length === 0 && !isLoading && (
              <span className="ws-nav-empty">No projects yet</span>
            )}
            {projects.map((project) => (
              <FilesProjectItem
                key={project.id}
                project={project}
                isExpanded={!!filesOpen[project.id]}
                isActive={project.id === activeProjectId}
                onToggle={() =>
                  setFilesOpen((prev) => ({ ...prev, [project.id]: !prev[project.id] }))
                }
              />
            ))}
          </div>

          {/* ── PROJECTS section ── */}
          <div className="ws-nav-section">
            <span className="ws-nav-section-label">Projects</span>
            {projects.map((project) => (
              <ProjectsTreeItem
                key={project.id}
                project={project}
                isExpanded={!!projectsOpen[project.id]}
                isActive={project.id === activeProjectId}
                activeConversationId={activeConversationId}
                onToggle={() =>
                  setProjectsOpen((prev) => ({ ...prev, [project.id]: !prev[project.id] }))
                }
                onNewConversation={() => setNewConvProjectId(project.id)}
              />
            ))}
          </div>
        </nav>

        <div className="ws-sidebar-footer">
          <span className="ws-user-email" title={user?.email}>{user?.email}</span>
          <button className="ws-sign-out" type="button" onClick={handleSignOut} title="Sign out">
            <LogOut size={14} />
          </button>
        </div>
      </aside>

      {showNewProject && (
        <NewProjectModal
          onConfirm={handleCreateProject}
          onCancel={() => setShowNewProject(false)}
          loading={createProject.isPending}
        />
      )}
      {newConvProjectId && (
        <NewConversationModal
          onConfirm={handleCreateConversation}
          onCancel={() => setNewConvProjectId(null)}
          loading={createConversation.isPending}
        />
      )}
    </>
  )
}

function FilesProjectItem({ project, isExpanded, isActive, onToggle }) {
  const { data: detail } = useProject(isExpanded ? project.id : null)
  const files = detail?.files ?? []

  return (
    <div className="ws-tree-item">
      <button
        className={`ws-tree-row ${isActive ? 'is-active' : ''}`}
        type="button"
        onClick={onToggle}
      >
        <ChevronRight size={12} className={`ws-chevron ${isExpanded ? 'is-open' : ''}`} />
        <FolderOpen size={13} className="ws-tree-icon" />
        <span className="ws-tree-label" title={project.name}>{project.name}</span>
      </button>

      {isExpanded && (
        <div className="ws-tree-children">
          {files.length === 0 ? (
            <span className="ws-leaf-empty">No files uploaded</span>
          ) : (
            files.map((file) => (
              <div key={file.id} className="ws-leaf ws-leaf-file">
                <FileText size={11} className="ws-leaf-icon" />
                <span className="ws-leaf-label" title={file.original_name}>
                  {file.original_name}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function ProjectsTreeItem({
  project, isExpanded, isActive, activeConversationId, onToggle, onNewConversation,
}) {
  const navigate = useNavigate()
  const { data: detail } = useProject(isExpanded ? project.id : null)
  const files = detail?.files ?? []
  const conversations = detail?.conversations ?? []

  return (
    <div className="ws-tree-item">
      <button
        className={`ws-tree-row ${isActive ? 'is-active' : ''}`}
        type="button"
        onClick={onToggle}
      >
        <ChevronRight size={12} className={`ws-chevron ${isExpanded ? 'is-open' : ''}`} />
        <span
          className="ws-tree-label"
          title={project.name}
          onClick={(e) => { e.stopPropagation(); navigate(`/projects/${project.id}`) }}
        >
          {project.name}
        </span>
      </button>

      {isExpanded && (
        <div className="ws-tree-children">
          {/* Files count row */}
          <div
            className="ws-leaf ws-leaf-meta"
            onClick={() => navigate(`/projects/${project.id}`)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigate(`/projects/${project.id}`)}
          >
            <FileText size={11} className="ws-leaf-icon" />
            <span className="ws-leaf-label">Files ({files.length})</span>
          </div>

          {/* Conversations count row */}
          <div className="ws-leaf ws-leaf-meta-passive">
            <MessageSquare size={11} className="ws-leaf-icon" />
            <span className="ws-leaf-label">Conversations ({conversations.length})</span>
          </div>

          {/* Individual conversations */}
          {conversations.map((conv) => (
            <Link
              key={conv.id}
              to={`/projects/${project.id}/conversations/${conv.id}`}
              className={`ws-leaf ws-leaf-conv ${conv.id === activeConversationId ? 'is-active' : ''}`}
            >
              <span className="ws-leaf-dash">—</span>
              <span className="ws-leaf-label" title={conv.title}>{conv.title}</span>
            </Link>
          ))}

          {/* New conversation button */}
          <button className="ws-leaf ws-leaf-add" type="button" onClick={onNewConversation}>
            <Plus size={11} />
            <span>New conversation</span>
          </button>
        </div>
      )}
    </div>
  )
}
