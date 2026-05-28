import { Navigate, Route, Routes } from 'react-router-dom'
import { PublicLayout } from './components/layout/PublicLayout'
import { WorkspaceLayout } from './components/workspace/WorkspaceLayout'
import { useAuth } from './context/AuthContext'
import { AuthPage } from './pages/AuthPage'
import { ComputerPage } from './pages/ComputerPage'
import { HomePage } from './pages/HomePage'

function ProtectedRoute({ children }) {
  const { session, loading } = useAuth()
  if (loading) return <div className="ws-loading">Loading...</div>
  if (!session) return <Navigate to="/review" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/review" element={<AuthPage />} />
      </Route>

      <Route
        path="/computer"
        element={
          <ProtectedRoute>
            <WorkspaceLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ComputerPage />} />
      </Route>

      <Route path="/projects/*" element={<Navigate to="/computer" replace />} />
      <Route path="/scoring" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
