import { useRef, useState, useCallback } from 'react'
import { Send, Paperclip, X } from 'lucide-react'

export function MessageInput({ disabled, onSend }) {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState([])
  const [isDragOver, setIsDragOver] = useState(false)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  function addFiles(fileList) {
    setAttachedFiles((prev) => [...prev, ...Array.from(fileList)])
  }

  function removeFile(index) {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  function submit() {
    const trimmed = text.trim()
    if ((!trimmed && attachedFiles.length === 0) || disabled) return
    onSend({ text: trimmed, files: attachedFiles })
    setText('')
    setAttachedFiles([])
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => setIsDragOver(false), [])

  return (
    <div className="conv-input-area">
      <div
        className={`conv-input-drop-zone ${isDragOver ? 'is-drag-over' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {attachedFiles.length > 0 && (
          <div className="conv-input-files">
            {attachedFiles.map((file, i) => (
              <span key={i} className="conv-input-file-pill">
                {file.name}
                <button type="button" onClick={() => removeFile(i)} aria-label="Remove file">
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="conv-input-row">
          <textarea
            ref={textareaRef}
            className="conv-textarea"
            placeholder={isDragOver ? 'Drop files here…' : 'Ask a question about the documents…'}
            value={text}
            disabled={disabled}
            rows={1}
            onChange={(e) => { setText(e.target.value); autoResize() }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
          />
          <button
            type="button"
            className="conv-attach-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Attach files"
            disabled={disabled}
          >
            <Paperclip size={17} />
          </button>
          <button
            type="button"
            className="conv-send-btn"
            disabled={disabled || (!text.trim() && attachedFiles.length === 0)}
            onClick={submit}
            title="Send (Enter)"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files.length) addFiles(e.target.files); e.target.value = '' }}
      />
    </div>
  )
}
