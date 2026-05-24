import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Check } from 'lucide-react'
import { MODELS } from '../../lib/models'
import { useModel } from '../../context/ModelContext'

export function ModelPicker({ disabled = false }) {
  const { modelId, model, setModelId } = useModel()
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)

  useEffect(() => {
    if (!open) return
    function onDocClick(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false)
    }
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function choose(id) {
    setModelId(id)
    setOpen(false)
  }

  return (
    <div className="model-picker" ref={rootRef}>
      <button
        type="button"
        className="model-picker-trigger"
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
        title="Switch model"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="model-picker-label">{model.label}</span>
        <ChevronDown size={13} />
      </button>

      {open && (
        <ul className="model-picker-menu" role="listbox">
          {MODELS.map((m) => {
            const active = m.id === modelId
            return (
              <li
                key={m.id}
                role="option"
                aria-selected={active}
                className={`model-picker-item ${active ? 'is-active' : ''}`}
                onClick={() => choose(m.id)}
              >
                <div className="model-picker-item-text">
                  <span className="model-picker-item-label">{m.label}</span>
                  <span className="model-picker-item-sub">{m.sublabel}</span>
                </div>
                {active && <Check size={14} className="model-picker-check" />}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
