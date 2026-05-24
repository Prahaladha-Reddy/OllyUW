import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function WorkspaceLayout() {
  return (
    <div className="workspace-shell">
      <Sidebar />
      <main className="ws-main">
        <Outlet />
      </main>
    </div>
  )
}
