import { useState } from 'react'
import {
  ArrowLeft,
  Eye,
  EyeOff,
  KeyRound,
  LogIn,
  Mail,
  UserPlus,
} from 'lucide-react'

import { supabase } from '../lib/supabase'

const modes = {
  SIGN_IN: 'sign-in',
  SIGN_UP: 'sign-up',
  RESET: 'reset',
}

export default function AuthCard() {
  const [mode, setMode] = useState(modes.SIGN_IN)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  function clearMessages() {
    setMessage('')
    setErrorMessage('')
  }

  function changeMode(nextMode) {
    clearMessages()
    setMode(nextMode)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    clearMessages()

    const cleanEmail = email.trim().toLowerCase()

    if (!cleanEmail) {
      setErrorMessage('Enter your email address.')
      return
    }

    if (mode !== modes.RESET && password.length < 8) {
      setErrorMessage('Password must contain at least 8 characters.')
      return
    }

    if (mode === modes.SIGN_UP && password !== confirmPassword) {
      setErrorMessage('Passwords do not match.')
      return
    }

    setBusy(true)

    try {
      if (mode === modes.SIGN_IN) {
        const { error } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password,
        })

        if (error) throw error
      }

      if (mode === modes.SIGN_UP) {
        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
          options: {
            emailredirectTo: `${window.location.origin}/update-password`,
          },
        })

        if (error) throw error

        if (!data.session) {
          setMessage(
            'Account created. Check your email to confirm your account, then sign in.',
          )
        }
      }

      if (mode === modes.RESET) {
        const { error } = await supabase.auth.resetPasswordForEmail(
          cleanEmail,
          {
            redirectTo: `${window.location.origin}/update-password`,
          },
        )

        if (error) throw error

        setMessage('Password reset instructions were sent to your email.')
      }
    } catch (error) {
      setErrorMessage(error.message || 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }

  const title =
    mode === modes.SIGN_IN
      ? 'Welcome back'
      : mode === modes.SIGN_UP
        ? 'Create your account'
        : 'Reset your password'

  const subtitle =
    mode === modes.SIGN_IN
      ? 'Secure access to forecasts, subscriptions, and prediction history.'
      : mode === modes.SIGN_UP
        ? 'Every new account begins on the Free plan.'
        : 'We will email you a secure password-reset link.'

  return (
    <main className="auth-shell">
      <div className="space-orb orb-one" />
      <div className="space-orb orb-two" />

      <section className="auth-card glass-card">
        <div className="auth-brand-block">
          <img className="auth-logo" src="/logo.png" alt="DiMarket logo" />
          <div className="auth-tagline">TRUSTWORTHY AI FORECASTING</div>
        </div>

        <h1>{title}</h1>
        <p className="auth-subtitle">{subtitle}</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Email
            <div className="input-wrap">
              <Mail size={20} />
              <input
                autoComplete="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Enter your email"
              />
            </div>
          </label>

          {mode !== modes.RESET && (
            <label>
              Password
              <div className="input-wrap">
                <KeyRound size={20} />
                <input
                  autoComplete={
                    mode === modes.SIGN_IN
                      ? 'current-password'
                      : 'new-password'
                  }
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                />
                <button
                  className="icon-button"
                  type="button"
                  aria-label="Toggle password visibility"
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </label>
          )}

          {mode === modes.SIGN_UP && (
            <label>
              Confirm password
              <div className="input-wrap">
                <KeyRound size={20} />
                <input
                  autoComplete="new-password"
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(event.target.value)
                  }
                  placeholder="Repeat your password"
                />
              </div>
            </label>
          )}

          {errorMessage && (
            <div className="notice notice-error">{errorMessage}</div>
          )}

          {message && <div className="notice notice-success">{message}</div>}

          <button className="primary-button" disabled={busy} type="submit">
            {mode === modes.SIGN_IN && <LogIn size={20} />}
            {mode === modes.SIGN_UP && <UserPlus size={20} />}
            {mode === modes.RESET && <Mail size={20} />}
            {busy
              ? 'Please wait...'
              : mode === modes.SIGN_IN
                ? 'Sign in'
                : mode === modes.SIGN_UP
                  ? 'Create account'
                  : 'Send reset email'}
          </button>
        </form>

        <div className="auth-actions">
          {mode === modes.SIGN_IN && (
            <>
              <button
                className="text-button"
                type="button"
                onClick={() => changeMode(modes.SIGN_UP)}
              >
                Create account
              </button>
              <button
                className="text-button"
                type="button"
                onClick={() => changeMode(modes.RESET)}
              >
                Forgot password?
              </button>
            </>
          )}

          {mode !== modes.SIGN_IN && (
            <button
              className="text-button"
              type="button"
              onClick={() => changeMode(modes.SIGN_IN)}
            >
              <ArrowLeft size={16} />
              Back to sign in
            </button>
          )}
        </div>
      </section>
    </main>
  )
}
