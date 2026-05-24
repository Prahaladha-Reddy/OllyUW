import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Trash2, FileText, Loader2, AlertCircle, MoreHorizontal, Plus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  useProject,
  useDeleteProject,
  useUploadProjectFiles,
  useDeleteProjectFile,
  useCreateConversation,
  useDeleteConversation,
} from '../hooks/queries'
import { sendConversationMessage } from '../lib/api'
import { MessageInput } from '../components/workspace/MessageInput'
import { formatRelativeDate } from '../utils/format'

function deriveTitle(message) {
  const trimmed = message.trim().replace(/\s+/g, ' ')
  if (trimmed.length <= 40) return trimmed || 'New conversation'
  return trimmed.slice(0, 40).trim() + '…'
}

export function ProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { session } = useAuth()
  const { data: project, isLoading, error } = useProject(projectId)
  const [menuOpen, setMenuOpen] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const menuRef = useRef(null)

  const deleteProject = useDeleteProject()
  const uploadFiles = useUploadProjectFiles(projectId)
  const deleteFile = useDeleteProjectFile(projectId)
  const createConversation = useCreateConversation(projectId)
  const deleteConversation = useDeleteConversation(projectId)

  const files = project?.files ?? []
  const conversations = project?.conversations ?? []

  useEffect(() => {
    function onClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
    }
    if (menuOpen) document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuOpen])

  async function handleStartConversation({ text, files: attached }) {
    if (isStarting || !text.trim()) return
    setIsStarting(true)
    try {
      if (attached?.length) await uploadFiles.mutateAsync(attached)
      const result = await createConversation.mutateAsync({ title: deriveTitle(text) })
      const newId = result.id ?? result.conversation_id

      await sendConversationMessage(session, projectId, newId, text.trim())
      navigate(`/projects/${projectId}/conversations/${newId}`)
    } catch (err) {
      console.error(err)
      setIsStarting(false)
    }
  }

  async function handleDeleteFile(file) {
    if (!window.confirm(`Delete "${file.original_name}"?`)) return
    await deleteFile.mutateAsync(file.id)
  }

  async function handleDeleteConversation(conv, e) {
    e.preventDefault()
    e.stopPropagation()
    if (!window.confirm(`Delete "${conv.title}"?`)) return
    await deleteConversation.mutateAsync(conv.id)
  }

  async function handleDeleteProject() {
    setMenuOpen(false)
    if (!window.confirm(`Delete "${project.name}" and all its data?`)) return
    await deleteProject.mutateAsync(projectId)
    navigate('/projects', { replace: true })
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
    <div className="pd-page">
      <div className="pd-breadcrumb">
        <Link to="/projects" className="pd-breadcrumb-link">Projects</Link>
        <span className="pd-breadcrumb-sep">/</span>
        <span className="pd-breadcrumb-current">{project.name}</span>

        <div className="pd-menu-wrap" ref={menuRef}>
          <button
            className="pd-menu-trigger"
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            title="More"
          >
            <MoreHorizontal size={15} />
          </button>
          {menuOpen && (
            <div className="pd-menu">
              <button
                className="pd-menu-item pd-menu-danger"
                type="button"
                onClick={handleDeleteProject}
                disabled={deleteProject.isPending}
              >
                <Trash2 size={13} />
                Delete project
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="pd-content">
        <h1 className="pd-title">{project.name}</h1>
        {project.description && (
          <p className="pd-description">{project.description}</p>
        )}

        <div className="pd-input-wrap">
          <MessageInput
            disabled={isStarting}
            onSend={handleStartConversation}
            placeholder={`Ask a question about ${project.name}…`}
          />
        </div>

        {files.length > 0 && (
          <section className="pd-list-section">
            <FilesList
              files={files}
              onDelete={handleDeleteFile}
              onAdd={(files) => uploadFiles.mutateAsync(files)}
              isUploading={uploadFiles.isPending}
            />
          </section>
        )}

        {files.length === 0 && (
          <section className="pd-list-section">
            <EmptyAddFiles
              onAdd={(files) => uploadFiles.mutateAsync(files)}
              isUploading={uploadFiles.isPending}
            />
          </section>
        )}

        {conversations.length > 0 && (
          <section className="pd-list-section">
            <div className="pd-list-header">Conversations</div>
            <div className="pd-flat-list">
              {conversations.map((conv) => (
                <Link
                  key={conv.id}
                  to={`/projects/${projectId}/conversations/${conv.id}`}
                  className="pd-row pd-row-conv"
                >
                  <span className="pd-row-title">{conv.title}</span>
                  <span className="pd-row-date">{formatRelativeDate(conv.created_at)}</span>
                  <button
                    className="pd-row-delete"
                    type="button"
                    onClick={(e) => handleDeleteConversation(conv, e)}
                    title="Delete conversation"
                    aria-label="Delete conversation"
                  >
                    <Trash2 size={13} />
                  </button>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function FilesList({ files, onDelete, onAdd, isUploading }) {
  const fileInputRef = useRef(null)
  return (
    <>
      <div className="pd-list-header">
        <span>Files</span>
        <button
          className="pd-add-inline"
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          <Plus size={12} />
          {isUploading ? 'Uploading…' : 'Add'}
        </button>
      </div>
      <div className="pd-flat-list">
        {files.map((file) => (
          <div key={file.id} className="pd-row pd-row-file">
            <FileText size={13} className="pd-row-icon" />
            <span className="pd-row-title" title={file.original_name}>{file.original_name}</span>
            {file.status && file.status !== 'ready' && (
              <span className={`pd-row-status pd-status-${file.status}`}>{file.status}</span>
            )}
            <button
              className="pd-row-delete"
              type="button"
              onClick={() => onDelete(file)}
              title="Delete file"
              aria-label="Delete file"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files.length) onAdd(Array.from(e.target.files)); e.target.value = '' }}
      />
    </>
  )
}

function EmptyAddFiles({ onAdd, isUploading }) {
  const fileInputRef = useRef(null)
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length) onAdd(Array.from(e.dataTransfer.files))
  }, [onAdd])

  return (
    <>
      <button
        type="button"
        className={`pd-add-files-quiet ${isDragOver ? 'is-drag-over' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
        onDragLeave={() => setIsDragOver(false)}
        disabled={isUploading}
      >
        <Plus size={12} />
        {isUploading ? 'Uploading…' : 'Add files to this project'}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files.length) onAdd(Array.from(e.target.files)); e.target.value = '' }}
      />
    </>
  )
}
