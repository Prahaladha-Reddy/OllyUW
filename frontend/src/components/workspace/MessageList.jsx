import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FileText } from 'lucide-react'

const MD_OPTS = { remarkPlugins: [remarkGfm] }

function MarkdownContent({ children }) {
  return <ReactMarkdown {...MD_OPTS}>{children}</ReactMarkdown>
}

export function MessageList({
  messages = [],
  optimisticUserMessage = null,
  streamingText = '',
  isStreaming = false,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, streamingText, isStreaming])

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
          <div className="msg-bubble">
            <MarkdownContent>{streamingText}</MarkdownContent>
            <span className="typing-cursor" />
          </div>
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
