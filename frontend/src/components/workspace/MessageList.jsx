import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FileText, Sparkles, Wrench, Check, AlertCircle, Loader2 } from 'lucide-react'
import { getModel } from '../../lib/models'

const MD_OPTS = { remarkPlugins: [remarkGfm] }

function MarkdownContent({ children }) {
  return <ReactMarkdown {...MD_OPTS}>{children}</ReactMarkdown>
}

function ModelTag({ modelId }) {
  if (!modelId) return null
  const m = getModel(modelId)
  return (
    <span className="msg-model-tag" title={m.sublabel}>
      <Sparkles size={10} />
      {m.label}
    </span>
  )
}

function summariseArgs(args) {
  if (!args || typeof args !== 'object') return ''
  const parts = []
  for (const [k, v] of Object.entries(args)) {
    let s
    if (typeof v === 'string') s = v.length > 40 ? v.slice(0, 40) + '…' : v
    else s = JSON.stringify(v)
    parts.push(`${k}: ${s}`)
    if (parts.join(', ').length > 80) break
  }
  return parts.join(', ')
}

function ToolCallChip({ tool, args, status }) {
  const Icon = status === 'done' ? Check
    : status === 'error' ? AlertCircle
    : Loader2
  return (
    <span className={`tool-chip tool-chip-${status}`}>
      <Wrench size={11} />
      <span className="tool-chip-name">{tool}</span>
      {args && <span className="tool-chip-args">({summariseArgs(args)})</span>}
      <Icon size={11} className={status === 'running' ? 'spin' : ''} />
    </span>
  )
}

export function MessageList({
  messages = [],
  optimisticUserMessage = null,
  streamingText = '',
  streamingModel = null,
  liveToolCalls = [],
  liveStatus = null,
  isStreaming = false,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, streamingText, isStreaming, liveToolCalls.length])

  const isEmpty =
    messages.length === 0 && !optimisticUserMessage && !isStreaming

  if (isEmpty) {
    return (
      <div className="conv-empty">
        <span>No messages yet.</span>
        <span style={{ fontSize: '0.8125rem' }}>Ask a question about the uploaded documents.</span>
      </div>
    )
  }

  // Streaming bubble has content when either (a) the model has emitted any
  // visible text, or (b) any tool calls have happened. Until then we show a
  // small status line so the user never stares at an empty rectangle.
  const streamingHasContent = !!streamingText || liveToolCalls.length > 0

  return (
    <div className="conv-messages">
      {messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}

      {optimisticUserMessage && (
        <div className="msg msg-user">
          <div className="msg-bubble">{optimisticUserMessage}</div>
        </div>
      )}

      {isStreaming && (
        <div className="msg msg-assistant msg-streaming">
          {liveToolCalls.length > 0 && (
            <div className="msg-tool-strip">
              {liveToolCalls.map((tc) => (
                <ToolCallChip key={tc.id} tool={tc.tool} args={tc.args} status={tc.status} />
              ))}
            </div>
          )}

          {streamingHasContent ? (
            <div className="msg-bubble">
              {streamingText
                ? <MarkdownContent>{streamingText}</MarkdownContent>
                : <span className="msg-status-inline">Working…</span>}
              <span className="typing-cursor" />
            </div>
          ) : (
            <div className="msg-status-row">
              <Loader2 size={13} className="spin" />
              <span>{liveStatus || 'Thinking…'}</span>
            </div>
          )}

          <ModelTag modelId={streamingModel} />
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

function Message({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`msg ${isUser ? 'msg-user' : 'msg-assistant'}`}>
      <div className="msg-bubble">
        {isUser ? message.content : <MarkdownContent>{message.content}</MarkdownContent>}
      </div>
      {!isUser && <ModelTag modelId={message.model} />}
      {!isUser && message.citations?.length > 0 && (
        <div className="msg-citations">
          {message.citations.map((c, i) => (
            <span key={i} className="msg-citation">
              <FileText size={11} />
              {c.filename}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
