import { FolderOpen } from 'lucide-react'

export function WorkspaceWelcome() {
  return (
    <div className="ws-welcome">
      <FolderOpen size={32} style={{ color: '#d1d5db' }} />
      <p className="ws-welcome-title">Select or create a project</p>
      <p style={{ fontSize: '0.8125rem' }}>Use the sidebar to navigate your underwriting projects.</p>
    </div>
  )
}
