import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { DEFAULT_MODEL_ID, getModel } from '../lib/models'

const STORAGE_KEY = 'ollyuw:selected-model'
const ModelContext = createContext(null)

function readInitial() {
  if (typeof window === 'undefined') return DEFAULT_MODEL_ID
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return getModel(stored).id
}

export function ModelProvider({ children }) {
  const [modelId, setModelIdState] = useState(readInitial)

  const setModelId = useCallback((next) => {
    const resolved = getModel(next).id
    setModelIdState(resolved)
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, modelId)
    } catch {
      // localStorage may be unavailable (private mode); the in-memory
      // state still works for the current session.
    }
  }, [modelId])

  return (
    <ModelContext.Provider value={{ modelId, setModelId, model: getModel(modelId) }}>
      {children}
    </ModelContext.Provider>
  )
}

export function useModel() {
  const ctx = useContext(ModelContext)
  if (!ctx) throw new Error('useModel must be used inside <ModelProvider>')
  return ctx
}
