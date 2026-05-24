import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom'
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
  const location = useLocation()
  const navigate = useNavigate()
  const { session } = useAuth()
  const { modelId } = useModel()

  const { data: project } = useProject(projectId)
  const { data: messages = [], isLoading, error } = useMessages(projectId, conversationId)

  // Local UI state for in-flight send:
  //   optimisticUserMsg  — text user just submitted (shown immediately, no server round-trip)
  //   streamingText      — accumulated `text_delta` deltas during streaming
  //   liveToolCalls      — tool calls the agent fired during this turn (visible as chips)
  //   liveStatus         — most recent `status` event (e.g. "Step 2/12")
  //   isSending          — true between submit and end-of-stream
  const [optimisticUserMsg, setOptimisticUserMsg] = useState(null)
  const [streamingText, setStreamingText] = useState('')
  const [liveToolCalls, setLiveToolCalls] = useState([])
  const [liveStatus, setLiveStatus] = useState(null)
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
    setLiveToolCalls([])
    setLiveStatus('Starting…')

    try {
      if (files?.length) await uploadFiles.mutateAsync(files)
      await sendMessage.mutateAsync({ text, model: modelId })

      // Create the abort controller only after the send POST completes.
      // If we created it before the first await, React Strict Mode's
      // synchronous cleanup (mount → cleanup → remount) would abort it
      // before streamConversation even opens, causing a silent AbortError
      // that clears the UI without showing the response.
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      for await (const event of streamConversation(
        session, projectId, conversationId, controller.signal,
      )) {
        switch (event.type) {
          case 'text_delta':
            setStreamingText((prev) => prev + (event.text ?? ''))
            break
          case 'status':
            if (event.text) setLiveStatus(event.text)
            break
          case 'tool_call':
            setLiveToolCalls((prev) => [
              ...prev,
              { id: event.id, tool: event.tool, args: event.args, status: 'running' },
            ])
            setLiveStatus(`Calling ${event.tool}…`)
            break
          case 'tool_result':
            setLiveToolCalls((prev) =>
              prev.map((t) =>
                t.id === event.id ? { ...t, status: event.ok ? 'done' : 'error', output: event.output } : t,
              ),
            )
            break
          case 'error':
            throw new Error(event.text || 'Agent worker failed')
          case 'final':
            break
        }
        if (event.type === 'final') break
      }

      // Wait for the new messages to land in the cache before clearing
      // the in-flight UI — otherwise the streaming bubble disappears and
      // the final assistant bubble pops in a beat later, which is what
      // causes the "blinking rectangle" the user saw.
      await queryClient.refetchQueries({
        queryKey: ['messages', projectId, conversationId],
        type: 'active',
      })
    } catch (err) {
      if (err.name !== 'AbortError') {
        setSendError(err.message ?? 'Something went wrong. Try again.')
      }
    } finally {
      abortRef.current?.abort()
      setOptimisticUserMsg(null)
      setStreamingText('')
      setLiveToolCalls([])
      setLiveStatus(null)
      setIsSending(false)
    }
  }, [session, projectId, conversationId, isSending, modelId, uploadFiles, sendMessage])

  // First-message handoff from ProjectDetail. When a conversation is created
  // by typing in the project chat-bar, the text is passed via nav state so
  // we can fire the send+stream here without the user having to retype.
  const initialFiredRef = useRef(false)
  useEffect(() => {
    const initial = location.state?.initialMessage
    if (!initial || initialFiredRef.current || !session) return
    initialFiredRef.current = true
    // Clear nav state so a refresh doesn't re-send the message.
    navigate(location.pathname, { replace: true, state: {} })
    handleSend({ text: initial, files: [] })
  }, [location.state, location.pathname, navigate, session, handleSend])

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
        liveToolCalls={liveToolCalls}
        liveStatus={liveStatus}
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
