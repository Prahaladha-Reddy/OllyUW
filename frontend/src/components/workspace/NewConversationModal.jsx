import { useState } from 'react'

export function NewConversationModal({ onConfirm, onCancel, loading }) {
  const [title, setTitle] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (title.trim()) onConfirm({ title: title.trim() })
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">New conversation</h2>
        <form onSubmit={handleSubmit}>
          <div className="modal-field">
            <label className="modal-label" htmlFor="conv-title">Title</label>
            <input
              id="conv-title"
              className="modal-input"
              type="text"
              placeholder="Liability analysis"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="modal-cancel" onClick={onCancel}>Cancel</button>
            <button type="submit" className="modal-submit" disabled={loading || !title.trim()}>
              {loading ? 'Creating…' : 'Start'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
