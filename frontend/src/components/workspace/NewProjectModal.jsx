import { useState } from 'react'

export function NewProjectModal({ onConfirm, onCancel, loading }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (name.trim()) onConfirm({ name: name.trim(), description: description.trim() || null })
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">New project</h2>
        <form onSubmit={handleSubmit}>
          <div className="modal-field">
            <label className="modal-label" htmlFor="proj-name">Name</label>
            <input
              id="proj-name"
              className="modal-input"
              type="text"
              placeholder="Acme AI — Series B"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="modal-field">
            <label className="modal-label" htmlFor="proj-desc">Description (optional)</label>
            <input
              id="proj-desc"
              className="modal-input"
              type="text"
              placeholder="Brief note about this review"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="modal-cancel" onClick={onCancel}>Cancel</button>
            <button type="submit" className="modal-submit" disabled={loading || !name.trim()}>
              {loading ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
