import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { PublicLayout } from './components/layout/PublicLayout'
import { HomePage } from './pages/HomePage'
import { AuthPage } from './pages/AuthPage'
import { ScoringPage } from './pages/ScoringPage'
import { WorkspaceLayout } from './components/workspace/WorkspaceLayout'
import { WorkspaceWelcome } from './pages/WorkspaceWelcome'
import { ProjectDetail } from './pages/ProjectDetail'
import { ConversationView } from './pages/ConversationView'

function ProtectedRoute({ children }) {
  const { session, loading } = useAuth()
  if (loading) return <div className="ws-loading">Loading…</div>
  if (!session) return <Navigate to="/review" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/review" element={<AuthPage />} />
        <Route path="/scoring" element={<ScoringPage />} />
      </Route>

      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <WorkspaceLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<WorkspaceWelcome />} />
        <Route path=":projectId" element={<ProjectDetail />} />
        <Route path=":projectId/conversations/:conversationId" element={<ConversationView />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
