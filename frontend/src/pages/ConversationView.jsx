import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useModel } from '../context/ModelContext'
import { useProject, useMessages, useUploadConversationFiles, useSendMessage } from '../hooks/queries'
import { queryClient } from '../lib/queryClient'
import { streamConversation } from '../lib/api'
import { MessageList } from '../components/workspace/MessageList'
import { MessageInput } from '../components/workspace/MessageInput'

export function ConversationView() {
  const { projectId, conversationId } = useParams()
  const { session } = useAuth()
  const { modelId } = useModel()

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
      await sendMessage.mutateAsync({ text, model: modelId })

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
  }, [session, projectId, conversationId, isSending, modelId])

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
      <div className="conv-header">
        <Link to={`/projects/${projectId}`} className="conv-header-breadcrumb">
          {project?.name ?? '…'}
        </Link>
        <span className="conv-header-sep">/</span>
        <span className="conv-header-title">{conversation?.title ?? 'Conversation'}</span>
      </div>

      {sendError && (
        <div className="conv-error-banner">{sendError}</div>
      )}

      <MessageList
        messages={messages}
        optimisticUserMessage={optimisticUserMsg}
        streamingText={streamingText}
        streamingModel={modelId}
        isStreaming={isSending}
      />

      <MessageInput
        disabled={isSending}
        onSend={handleSend}
        placeholder={project?.name ? `Ask a question about ${project.name}…` : 'Ask a question about the documents…'}
      />
    </div>
  )
}
