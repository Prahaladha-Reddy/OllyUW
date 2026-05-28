import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'

export function AuthPage() {
  const { session } = useAuth()
  const [mode, setMode] = useState('sign-in')
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState('Use your Olly account to continue.')
  const [loading, setLoading] = useState(false)
  const isSignUp = mode === 'sign-up'

  if (session) return <Navigate to="/computer" replace />

  function selectMode(nextMode) {
    setMode(nextMode)
    setMessage(
      nextMode === 'sign-up'
        ? 'Create an account to unlock your second computer.'
        : 'Use your Olly account to continue.',
    )
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const email = form.get('email')
    const password = form.get('password')

    setLoading(true)
    setMessage('')

    if (isSignUp) {
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) {
        setMessage(error.message)
      } else {
        setMessage('Check your email to confirm your account.')
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) setMessage(error.message)
    }

    setLoading(false)
  }

  return (
    <section className="page auth-page section-dark" aria-label="Sign in or sign up">
      <div className="auth-shell">
        <div className="auth-copy">
          <p className="eyebrow">Persistent AI Workspace</p>
          <h1>Unlock the computer your AI works from.</h1>
          <p>
            Files, sessions, and task history stay with the machine so the agent can keep working
            across visits instead of starting cold on every request.
          </p>
        </div>

        <div className="auth-card">
          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              className={`auth-tab ${mode === 'sign-in' ? 'is-active' : ''}`}
              type="button"
              role="tab"
              aria-selected={mode === 'sign-in'}
              onClick={() => selectMode('sign-in')}
            >
              Sign in
            </button>
            <button
              className={`auth-tab ${mode === 'sign-up' ? 'is-active' : ''}`}
              type="button"
              role="tab"
              aria-selected={mode === 'sign-up'}
              onClick={() => selectMode('sign-up')}
            >
              Sign up
            </button>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              required
            />

            <label htmlFor="password">Password</label>
            <div className="password-field">
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
                placeholder="Enter your password"
                required
              />
              <button
                className="icon-button"
                type="button"
                onClick={() => setShowPassword((c) => !c)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={20} strokeWidth={2} /> : <Eye size={20} strokeWidth={2} />}
              </button>
            </div>

            <button className="pill-button auth-submit" type="submit" disabled={loading}>
              {loading ? 'Loading…' : isSignUp ? 'Create account' : 'Continue'}
            </button>
            {message && <p className="form-note">{message}</p>}
          </form>
        </div>
      </div>
    </section>
  )
}
