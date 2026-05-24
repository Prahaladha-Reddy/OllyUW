import { useState, useCallback, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Plus, Trash2, FileText, Loader2, AlertCircle, Upload } from 'lucide-react'
import {
  useProject,
  useDeleteProject,
  useUploadProjectFiles,
  useDeleteProjectFile,
  useCreateConversation,
  useDeleteConversation,
} from '../hooks/queries'
import { NewConversationModal } from '../components/workspace/NewConversationModal'
import { formatDate } from '../utils/format'

export function ProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { data: project, isLoading, error } = useProject(projectId)
  const [showNewConv, setShowNewConv] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef(null)

  const deleteProject = useDeleteProject()
  const uploadFiles = useUploadProjectFiles(projectId)
  const deleteFile = useDeleteProjectFile(projectId)
  const createConversation = useCreateConversation(projectId)
  const deleteConversation = useDeleteConversation(projectId)

  const files = project?.files ?? []
  const conversations = project?.conversations ?? []

  async function handleUpload(fileList) {
    if (!fileList.length) return
    await uploadFiles.mutateAsync(Array.from(fileList))
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files)
  }, [projectId])

  async function handleDeleteFile(file) {
    if (!window.confirm(`Delete "${file.original_name}"?`)) return
    await deleteFile.mutateAsync(file.id)
  }

  async function handleDeleteConversation(conv) {
    if (!window.confirm(`Delete "${conv.title}"?`)) return
    await deleteConversation.mutateAsync(conv.id)
  }

  async function handleDeleteProject() {
    if (!window.confirm(`Delete "${project.name}" and all its data?`)) return
    await deleteProject.mutateAsync(projectId)
    navigate('/projects', { replace: true })
  }

  async function handleCreateConversation({ title }) {
    const result = await createConversation.mutateAsync({ title })
    const id = result.id ?? result.conversation_id
    setShowNewConv(false)
    navigate(`/projects/${projectId}/conversations/${id}`)
  }

  if (isLoading) {
    return (
      <div className="ws-loading">
        <Loader2 size={18} className="spin" /> Loading project…
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="ws-loading" style={{ flexDirection: 'column', gap: '0.5rem' }}>
        <AlertCircle size={20} />
        <span>Project not found.</span>
        <Link to="/projects" style={{ color: '#7d8590', fontSize: '0.875rem' }}>Go back</Link>
      </div>
    )
  }

  return (
    <>
      <div className="project-detail">
        <div className="project-detail-header">
          <h1 className="project-detail-title">{project.name}</h1>
          {project.description && (
            <p className="project-detail-description">{project.description}</p>
          )}
          <p className="project-detail-description" style={{ marginTop: '0.25rem' }}>
            Created {formatDate(project.created_at)}
          </p>
        </div>

        {/* Files */}
        <div className="pd-section">
          <div className="pd-section-header">
            <span className="pd-section-title">Files ({files.length})</span>
            <button
              className="pd-new-btn"
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadFiles.isPending}
            >
              <Upload size={14} />
              {uploadFiles.isPending ? 'Uploading…' : 'Upload'}
            </button>
          </div>

          <div
            className={`pd-upload-zone ${isDragOver ? 'is-drag-over' : ''}`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
            onDragLeave={() => setIsDragOver(false)}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
          >
            <p className="pd-upload-zone-text">
              {isDragOver ? 'Drop to upload' : 'Drop files here or click to browse'}
            </p>
          </div>

          {uploadFiles.isError && (
            <p style={{ color: '#dc2626', fontSize: '0.8125rem', marginTop: '0.5rem' }}>
              {uploadFiles.error?.message ?? 'Upload failed.'}
            </p>
          )}

          {files.length > 0 && (
            <div className="pd-file-list" style={{ marginTop: '0.75rem' }}>
              {files.map((file) => (
                <div key={file.id} className="pd-file-row">
                  <FileText size={15} style={{ color: '#484f58', flexShrink: 0 }} />
                  <span className="pd-file-name" title={file.original_name}>
                    {file.original_name}
                  </span>
                  <span className={`pd-file-status status-${file.status ?? 'ready'}`}>
                    {file.status ?? 'ready'}
                  </span>
                  <button
                    className="pd-delete-btn"
                    type="button"
                    onClick={() => handleDeleteFile(file)}
                    title="Delete file"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Conversations */}
        <div className="pd-section">
          <div className="pd-section-header">
            <span className="pd-section-title">Conversations ({conversations.length})</span>
            <button className="pd-new-btn" type="button" onClick={() => setShowNewConv(true)}>
              <Plus size={14} />
              New
            </button>
          </div>

          <div className="pd-conversation-list">
            {conversations.length === 0 ? (
              <p style={{ fontSize: '0.875rem', color: '#7d8590', fontFamily: 'var(--font-ui)' }}>
                No conversations yet. Start one above.
              </p>
            ) : (
              conversations.map((conv) => (
                <div key={conv.id} className="pd-conv-card-row">
                  <Link
                    to={`/projects/${projectId}/conversations/${conv.id}`}
                    className="pd-conv-card"
                  >
                    <span className="pd-conv-card-title">{conv.title}</span>
                    <span className="pd-conv-card-date">{formatDate(conv.created_at)}</span>
                  </Link>
                  <button
                    className="pd-delete-btn"
                    type="button"
                    onClick={() => handleDeleteConversation(conv)}
                    title="Delete conversation"
                    style={{ flexShrink: 0 }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Danger zone */}
        <div className="pd-section" style={{ borderTop: '1px solid #21262d', paddingTop: '1.5rem', marginTop: '1rem' }}>
          <button
            className="pd-new-btn"
            type="button"
            onClick={handleDeleteProject}
            disabled={deleteProject.isPending}
            style={{ color: '#f85149', borderColor: '#4a1515' }}
          >
            <Trash2 size={14} />
            {deleteProject.isPending ? 'Deleting…' : 'Delete project'}
          </button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files.length) handleUpload(e.target.files); e.target.value = '' }}
      />

      {showNewConv && (
        <NewConversationModal
          onConfirm={handleCreateConversation}
          onCancel={() => setShowNewConv(false)}
          loading={createConversation.isPending}
        />
      )}
    </>
  )
}
