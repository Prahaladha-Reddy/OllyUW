import { ChevronDown, Folder, Monitor, Plug, Settings } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  useComputer,
  useComputerConnections,
  useComputerFiles,
  useVaultItems,
} from '../../hooks/queries'

export function Sidebar() {
  const { signOut, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { data: computer } = useComputer()
  const { data: files = [] } = useComputerFiles()
  const { data: connections = [] } = useComputerConnections()
  const { data: vaultItems = [] } = useVaultItems()

  const rawName = user?.user_metadata?.full_name ?? user?.email?.split('@')[0] ?? 'User'
  const displayName = rawName.replace(/[._]/g, ' ')
  const initials = displayName[0]?.toUpperCase() ?? '?'
  const isComputerRoute = location.pathname.startsWith('/computer')

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  return (
    <aside className="ws-sidebar">
      <div className="ws-sidebar-header">
        <Link to={computer ? '/computer' : '/'} className="ws-sidebar-brand">Olly</Link>
      </div>

      <div className="ws-sidebar-actions">
        <button
          className={`ws-new-project-btn ${isComputerRoute ? 'is-active' : ''}`}
          type="button"
          onClick={() => navigate('/computer')}
        >
          <Monitor size={14} />
          Open computer
        </button>
      </div>

      <nav className="ws-sidebar-nav">
        <div className="ws-nav-section">
          <span className="ws-nav-section-label">Machine</span>
          <div className="ws-sidebar-status">
            <span className={`status-dot status-${computer?.status ?? 'pending'}`} />
            <span>{computer?.status === 'online' ? 'Online' : 'Sleeping'}</span>
          </div>
          <button className="ws-project-item is-active" type="button" onClick={() => navigate('/computer')}>
            <Monitor size={13} className="ws-project-icon" />
            <span className="ws-project-name">Your computer</span>
          </button>
        </div>

        <div className="ws-nav-section">
          <span className="ws-nav-section-label">State</span>
          <div className="ws-project-item" role="presentation">
            <Folder size={13} className="ws-project-icon" />
            <span className="ws-project-name">{files.length} files and folders</span>
          </div>
          <div className="ws-project-item" role="presentation">
            <Plug size={13} className="ws-project-icon" />
            <span className="ws-project-name">{connections.length} connected apps</span>
          </div>
          <div className="ws-project-item" role="presentation">
            <Settings size={13} className="ws-project-icon" />
            <span className="ws-project-name">{vaultItems.length} vault items saved</span>
          </div>
        </div>
      </nav>

      <div className="ws-sidebar-footer">
        <div className="ws-user-row">
          <div className="ws-user-avatar">{initials}</div>
          <div className="ws-user-meta">
            <span className="ws-user-name">{displayName}</span>
            <span className="ws-user-email-text">{user?.email}</span>
          </div>
          <ChevronDown size={13} className="ws-user-chevron" />
        </div>
        <div className="ws-footer-actions">
          <button className="ws-settings-btn" type="button" title="Sign out" onClick={handleSignOut}>
            <Settings size={13} />
          </button>
        </div>
      </div>
    </aside>
  )
}
