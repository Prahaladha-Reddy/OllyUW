import { Link } from 'react-router-dom'
import { Brand } from './Brand'
import { useAuth } from '../../context/AuthContext'

export function Header() {
  const { session } = useAuth()

  return (
    <header className="site-header">
      <Brand />
      {!session && (
        <Link className="pill-button" to="/review">Unlock computer</Link>
      )}
    </header>
  )
}
