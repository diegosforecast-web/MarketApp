import { useState } from 'react'
import {
  ArrowDown,
  ArrowLeft,
  BrainCircuit,
  ChartNoAxesCombined,
  Eye,
  EyeOff,
  History,
  KeyRound,
  LogIn,
  Mail,
  ShieldCheck,
  Sparkles,
  UserPlus,
} from 'lucide-react'

import { supabase } from '../lib/supabase'
import './AuthPage.css'

const TRUST_POINTS = [
  {
    icon: BrainCircuit,
    title: 'Explainable AI forecasts',
    description:
      'See expected movement, model confidence, supporting evidence, and risks.',
  },
  {
    icon: ChartNoAxesCombined,
    title: 'Historically validated',
    description:
      'Review transparent model-performance metrics instead of marketing claims.',
  },
  {
    icon: ShieldCheck,
    title: 'Confidence with context',
    description:
      'Understand uncertainty and why the model reached each decision.',
  },
  {
    icon: History,
    title: 'Predictions that remain accountable',
    description:
      'Save forecasts and compare them with real market outcomes over time.',
  },
]

export default function AuthPage() {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  function clearMessage() {
    setMessage('')
    setIsError(false)
  }

  function switchMode() {
    clearMessage()
    setMode((current) => (current === 'login' ? 'signup' : 'login'))
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    clearMessage()

    const cleanEmail = email.trim().toLowerCase()

    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password,
        })
        if (error) throw error
      } else {
        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
          options: {
            emailRedirectTo: window.location.origin,
          },
        })
        if (error) throw error

        if (!data.session) {
          setMessage(
            'Account created. Check your email to confirm it, then sign in.',
          )
        }
      }
    } catch (error) {
      setIsError(true)
      setMessage(error.message || 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }

  async function resetPassword() {
    clearMessage()
    const cleanEmail = email.trim().toLowerCase()

    if (!cleanEmail) {
      setIsError(true)
      setMessage('Enter your email first.')
      return
    }

    setBusy(true)

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(
        cleanEmail,
        {
          redirectTo: window.location.origin,
        },
      )
      if (error) throw error
      setMessage('Password reset email sent.')
    } catch (error) {
      setIsError(true)
      setMessage(error.message || 'Unable to send reset email.')
    } finally {
      setBusy(false)
    }
  }

  const isLogin = mode === 'login'

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
              AI FORECASTING FOR INDIVIDUAL INVESTORS
            </span>

            <h1>Markets are uncertain. Your research can be clearer.</h1>

            <p className="auth-purpose">
              DiMarket helps individual investors explore potential market
              direction, estimated price movement, model confidence, and the
              reasoning behind every forecast.
            </p>

            <div className="auth-trust-grid">
              {TRUST_POINTS.map(({ icon: Icon, title, description }) => (
                <article key={title}>
                  <div className="auth-trust-icon">
                    <Icon size={20} />
                  </div>
                  <div>
                    <strong>{title}</strong>
                    <p>{description}</p>
                  </div>
                </article>
              ))}
            </div>

            <div className="auth-mission-card">
              <Sparkles size={21} />
              <div>
                <span>OUR MISSION</span>
                <p>
                  Build the most trustworthy AI forecasting platform that an
                  individual investor can access.
                </p>
              </div>
            </div>
          </section>

          <section className="auth-access-panel">
            <span className="auth-eyebrow">
              {isLogin ? 'SECURE ACCESS' : 'START FREE'}
            </span>

            <h2>
              {isLogin ? 'Welcome back' : 'Create your free account'}
            </h2>

            <p className="auth-subtitle">
              {isLogin
                ? 'Access your forecasts, portfolio intelligence, watchlist, and prediction journal.'
                : 'Ready to experience a more transparent and trustworthy way to forecast the market? Join DiMarket for free.'}
            </p>

            {!isLogin && (
              <div className="auth-join-prompt">
                <span>Join us here for free</span>
                <ArrowDown size={19} />
              </div>
            )}

            <form className="auth-form" onSubmit={submit}>
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
                    required
                  />
                </div>
              </label>

              <label>
                Password
                <div className="input-wrap">
                  <KeyRound size={20} />
                  <input
                    autoComplete={
                      isLogin ? 'current-password' : 'new-password'
                    }
                    type={show ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your password"
                    minLength={8}
                    required
                  />

                  <button
                    className="icon-button"
                    type="button"
                    aria-label={show ? 'Hide password' : 'Show password'}
                    onClick={() => setShow((value) => !value)}
                  >
                    {show ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
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
                {isLogin ? <LogIn size={20} /> : <UserPlus size={20} />}
                {busy
                  ? 'Please wait...'
                  : isLogin
                    ? 'Sign in'
                    : 'Create free account'}
              </button>
            </form>

            <div className="auth-actions">
              <button
                className="text-button"
                type="button"
                onClick={switchMode}
              >
                {!isLogin && <ArrowLeft size={16} />}
                {isLogin
                  ? 'Create a free account'
                  : 'Back to sign in'}
              </button>

              {isLogin && (
                <button
                  className="text-button"
                  type="button"
                  onClick={resetPassword}
                  disabled={busy}
                >
                  Forgot password?
                </button>
              )}
            </div>
          </section>
        </div>

        <p className="auth-disclaimer">
          DiMarket forecasts are research tools based on historical market data
          and machine-learning models. They are not financial advice and cannot
          guarantee future results.
        </p>
      </section>
    </main>
  )
}
