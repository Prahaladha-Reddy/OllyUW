import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronRight, Loader2, AlertCircle, Upload, FileText } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useProject, useMessages, useUploadConversationFiles, useSendMessage } from '../hooks/queries'
import { queryClient } from '../lib/queryClient'
import { streamConversation } from '../lib/api'
import { MessageList } from '../components/workspace/MessageList'
import { MessageInput } from '../components/workspace/MessageInput'

export function ConversationView() {
  const { projectId, conversationId } = useParams()
  const { session } = useAuth()

  const { data: project } = useProject(projectId)
  const { data: messages = [], isLoading, error } = useMessages(projectId, conversationId)

  const [optimisticUserMsg, setOptimisticUserMsg] = useState(null)
  const [streamingText, setStreamingText] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState(null)

  const abortRef = useRef(null)
  const uploadFiles = useUploadConversationFiles(projectId, conversationId)
  const sendMessage = useSendMessage(projectId, conversationId)

  const conversation = project?.conversations?.find((c) => c.id === conversationId)
  const projectFiles = project?.files ?? []

  // Cleanup: if the component unmounts mid-stream, abort.
  useEffect(() => () => abortRef.current?.abort(), [])

  const handleSend = useCallback(async ({ text, files }) => {
    if (isSending) return
    setIsSending(true)
    setSendError(null)
    setOptimisticUserMsg(text)
    setStreamingText('')

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      if (files?.length) await uploadFiles.mutateAsync(files)
      await sendMessage.mutateAsync(text)

      for await (const event of streamConversation(
        session, projectId, conversationId, controller.signal,
      )) {
        if (event.type === 'text_delta') {
          setStreamingText((prev) => prev + (event.text ?? ''))
        } else if (event.type === 'final') {
          break
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setSendError(err.message ?? 'Something went wrong. Try again.')
      }
    } finally {
      controller.abort()
      setOptimisticUserMsg(null)
      setStreamingText('')
      setIsSending(false)
      queryClient.invalidateQueries({ queryKey: ['messages', projectId, conversationId] })
    }
  }, [session, projectId, conversationId, isSending])

  if (isLoading) {
    return (
      <div className="ws-loading">
        <Loader2 size={18} className="spin" /> Loading…
      </div>
    )
  }

  if (error) {
    return (
      <div className="ws-loading" style={{ flexDirection: 'column', gap: '0.5rem' }}>
        <AlertCircle size={20} />
        <span>Could not load conversation.</span>
        <Link to={`/projects/${projectId}`} style={{ color: '#7d8590', fontSize: '0.875rem' }}>
          Back to project
        </Link>
      </div>
    )
  }

  return (
    <div className="conv-view">
      {/* Header breadcrumb */}
      <div className="conv-header">
        <Link to="/projects" className="conv-header-breadcrumb">Projects</Link>
        <ChevronRight size={12} style={{ color: '#30363d' }} />
        <Link to={`/projects/${projectId}`} className="conv-header-breadcrumb">
          {project?.name ?? '…'}
        </Link>
        <ChevronRight size={12} style={{ color: '#30363d' }} />
        <span className="conv-header-title">{conversation?.title ?? 'Conversation'}</span>
      </div>

      {/* Error banner */}
      {sendError && (
        <div style={{
          padding: '0.5rem 1.5rem',
          background: '#2d1515',
          color: '#f85149',
          fontSize: '0.8125rem',
          fontFamily: 'var(--font-ui)',
          flexShrink: 0,
        }}>
          {sendError}
        </div>
      )}

      {/* Messages */}
      <MessageList
        messages={messages}
        optimisticUserMessage={optimisticUserMsg}
        streamingText={streamingText}
        isStreaming={isSending}
      />

      {/* File upload strip */}
      <ConvFileStrip
        projectId={projectId}
        conversationId={conversationId}
        projectFiles={projectFiles}
      />

      {/* Input */}
      <MessageInput disabled={isSending} onSend={handleSend} />
    </div>
  )
}

function ConvFileStrip({ projectId, conversationId, projectFiles }) {
  const [open, setOpen] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef(null)
  const uploadFiles = useUploadConversationFiles(projectId, conversationId)

  async function handleUpload(fileList) {
    if (!fileList.length) return
    await uploadFiles.mutateAsync(Array.from(fileList))
  }

  return (
    <div className="conv-upload-strip">
      <div className="conv-upload-header" onClick={() => setOpen((o) => !o)}>
        <span className="conv-upload-label">
          <FileText size={12} />
          Files ({projectFiles.length})
        </span>
        <span className="conv-upload-toggle">{open ? '▲ hide' : '▼ show'}</span>
      </div>

      {open && (
        <div className="conv-upload-body">
          {projectFiles.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginBottom: '0.5rem' }}>
              {projectFiles.map((f) => (
                <span key={f.id} className="msg-citation">
                  <FileText size={10} />
                  {f.original_name}
                </span>
              ))}
            </div>
          )}
          <div
            className={`conv-upload-zone ${isDragOver ? 'is-drag-over' : ''}`}
            onDrop={(e) => { e.preventDefault(); setIsDragOver(false); handleUpload(e.dataTransfer.files) }}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
            onDragLeave={() => setIsDragOver(false)}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
          >
            <Upload size={13} />
            <span>
              {uploadFiles.isPending
                ? 'Uploading…'
                : 'Add files to this project (drop or click)'}
            </span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => { if (e.target.files.length) handleUpload(e.target.files); e.target.value = '' }}
          />
          {uploadFiles.isError && (
            <p style={{ margin: '0.375rem 0 0', fontSize: '0.75rem', color: '#f85149', fontFamily: 'var(--font-ui)' }}>
              {uploadFiles.error?.message ?? 'Upload failed.'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
