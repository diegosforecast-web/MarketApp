import { useState } from 'react'
import { Eye, EyeOff, KeyRound, LockKeyhole } from 'lucide-react'

import { supabase } from '../lib/supabase'
import './AuthPage.css'

export default function UpdatePasswordPage() {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  async function updatePassword(event) {
    event.preventDefault()
    setMessage('')
    setIsError(false)

    if (password.length < 8) {
      setIsError(true)
      setMessage('Password must be at least 8 characters.')
      return
    }

    if (password !== confirmPassword) {
      setIsError(true)
      setMessage('Passwords do not match.')
      return
    }

    setBusy(true)

    try {
      const { error } = await supabase.auth.updateUser({ password })
      if (error) throw error

      setMessage('Password updated successfully. Redirecting...')
      setTimeout(() => {
        window.location.replace('/')
      }, 1500)
    } catch (error) {
      setIsError(true)
      setMessage(error.message || 'Unable to update password.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-shell auth-page-v2">
      <div className="space-orb orb-one" />
      <div className="space-orb orb-two" />

      <section className="auth-card auth-card-v2 glass-card">
        <div className="auth-brand-block">
          <img
            className="auth-logo auth-logo-v2"
            src="/logo.png"
            alt="DiMarket logo"
          />
          <div className="auth-tagline">
            TRUSTWORTHY AI FORECASTING
          </div>
        </div>

        <div className="auth-experience-grid">
          <section className="auth-introduction">
            <span className="auth-eyebrow">
              SECURE ACCOUNT RECOVERY
            </span>

            <h1>Create a new password.</h1>

            <p className="auth-purpose">
              Choose a strong password for your DiMarket account. Your new
              password must contain at least eight characters.
            </p>

            <div className="auth-mission-card">
              <LockKeyhole size={21} />
              <div>
                <span>SECURE RESET</span>
                <p>
                  After your password is updated, you will be returned to
                  DiMarket and can continue using your account.
                </p>
              </div>
            </div>
          </section>

          <section className="auth-access-panel">
            <span className="auth-eyebrow">PASSWORD RECOVERY</span>

            <h2>Set your new password</h2>

            <p className="auth-subtitle">
              Enter and confirm the password you would like to use.
            </p>

            <form className="auth-form" onSubmit={updatePassword}>
              <label>
                New password
                <div className="input-wrap">
                  <KeyRound size={20} />
                  <input
                    autoComplete="new-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your new password"
                    minLength={8}
                    required
                  />

                  <button
                    className="icon-button"
                    type="button"
                    aria-label={
                      showPassword ? 'Hide password' : 'Show password'
                    }
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword
                      ? <EyeOff size={20} />
                      : <Eye size={20} />}
                  </button>
                </div>
              </label>

              <label>
                Confirm new password
                <div className="input-wrap">
                  <KeyRound size={20} />
                  <input
                    autoComplete="new-password"
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                    placeholder="Confirm your new password"
                    minLength={8}
                    required
                  />
                </div>
              </label>

              {message && (
                <div
                  className={`notice ${
                    isError ? 'notice-error' : 'notice-success'
                  }`}
                >
                  {message}
                </div>
              )}

              <button
                className="primary-button"
                type="submit"
                disabled={busy}
              >
                <LockKeyhole size={20} />
                {busy ? 'Updating password...' : 'Update password'}
              </button>
            </form>
          </section>
        </div>

        <p className="auth-disclaimer">
          DiMarket will never ask you to send your password by email.
        </p>
      </section>
    </main>
  )
}
