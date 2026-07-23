import { useState } from 'react'
import {
  BadgeCheck,
  CalendarClock,
  CheckCircle2,
  CircleAlert,
  CreditCard,
  KeyRound,
  LogOut,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserCircle2,
} from 'lucide-react'

import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import './SettingsPanel.css'

const API_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const PLAN_NAMES = {
  free: 'Explorer',
  standard: 'Standard',
  premium: 'Premium',
  gold: 'Gold',
}

const PLAN_DESCRIPTIONS = {
  free: 'Complimentary access for discovering how DiMarket thinks.',
  standard:
    'Unlimited 1–3 day forecasts plus monthly 5-day credits.',
  premium:
    'Unlimited 1–5 day forecasts plus monthly 15-day credits.',
  gold:
    'The complete DiMarket experience across every production-supported horizon.',
}

function formatDate(value) {
  if (!value) return 'Not available'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return 'Not available'

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
  }).format(date)
}

function normalizeStatus(value, planKey) {
  const normalized = String(
    value || (planKey === 'free' ? 'free' : 'active'),
  )
    .trim()
    .toLowerCase()

  if (normalized === 'trialing') return 'Trial active'
  if (normalized === 'past_due') return 'Payment attention needed'
  if (normalized === 'canceled') return 'Canceled'
  if (normalized === 'inactive') return 'Inactive'
  if (normalized === 'free') return 'Complimentary access'
  if (normalized === 'active') return 'Active subscription'

  return normalized
    .split('_')
    .map(
      (part) =>
        part.charAt(0).toUpperCase() + part.slice(1),
    )
    .join(' ')
}

export default function SettingsPanel() {
  const {
    user,
    profile,
    entitlements,
    refreshAccount,
  } = useAuth()

  const [busyAction, setBusyAction] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const planKey = String(
    entitlements?.plan ||
      profile?.plan ||
      'free',
  ).toLowerCase()

  const planName = PLAN_NAMES[planKey] || 'Explorer'
  const subscriptionStatus = normalizeStatus(
    profile?.subscription_status ||
      entitlements?.subscription_status,
    planKey,
  )

  const displayName =
    profile?.full_name ||
    user?.user_metadata?.full_name ||
    user?.email?.split('@')[0] ||
    'DiMarket investor'

  const memberSince =
    profile?.created_at || user?.created_at

  const periodEnd =
    profile?.current_period_end ||
    entitlements?.period_end

  const emailVerified = Boolean(
    user?.email_confirmed_at ||
      user?.confirmed_at,
  )

  async function authenticatedPost(path) {
    const {
      data: { session },
    } = await supabase.auth.getSession()

    if (!session?.access_token) {
      throw new Error(
        'Your session has expired. Please sign in again.',
      )
    }

    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
    })

    const payload = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(
        payload?.detail ||
          `Request failed (${response.status}).`,
      )
    }

    return payload
  }

  async function openBilling() {
    setBusyAction('billing')
    setMessage('')
    setError('')

    try {
      if (planKey === 'free') {
        document
          .getElementById('plans')
          ?.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
          })

        setMessage(
          'Choose a paid experience below to activate billing.',
        )
        return
      }

      const payload = await authenticatedPost(
        '/billing/portal',
      )

      if (!payload?.url) {
        throw new Error(
          'Stripe did not return a billing portal URL.',
        )
      }

      window.location.assign(payload.url)
    } catch (requestError) {
      setError(
        requestError.message ||
          'Unable to open billing.',
      )
    } finally {
      setBusyAction('')
    }
  }

  async function sendPasswordReset() {
    setBusyAction('password')
    setMessage('')
    setError('')

    try {
      if (!user?.email) {
        throw new Error(
          'No email address is associated with this account.',
        )
      }

      const redirectTo = `${window.location.origin}/update-password`

      const { error: resetError } =
        await supabase.auth.resetPasswordForEmail(
          user.email,
          { redirectTo },
        )

      if (resetError) throw resetError

      setMessage(
        `Password reset instructions were sent to ${user.email}.`,
      )
    } catch (requestError) {
      setError(
        requestError.message ||
          'Unable to send password reset instructions.',
      )
    } finally {
      setBusyAction('')
    }
  }

  async function refreshProfile() {
    setBusyAction('refresh')
    setMessage('')
    setError('')

    try {
      await refreshAccount()
      setMessage('Account information refreshed.')
    } catch (requestError) {
      setError(
        requestError.message ||
          'Unable to refresh account information.',
      )
    } finally {
      setBusyAction('')
    }
  }

  async function signOut() {
    setBusyAction('logout')
    setMessage('')
    setError('')

    const { error: signOutError } =
      await supabase.auth.signOut()

    if (signOutError) {
      setBusyAction('')
      setError(signOutError.message)
    }
  }

  return (
    <section id="settings" className="settings-panel">
      <div className="section-heading settings-heading">
        <div>
          <span className="dashboard-eyebrow">
            ACCOUNT & ACCESS
          </span>
          <h2>Settings</h2>
          <p>
            Review your identity, subscription, billing,
            and account-security controls.
          </p>
        </div>

        <ShieldCheck size={30} />
      </div>

      <div
        className={`settings-account-hero settings-account-${planKey}`}
      >
        <div className="settings-account-hero-icon">
          {planKey === 'gold' ? (
            <Sparkles size={28} />
          ) : (
            <UserCircle2 size={28} />
          )}
        </div>

        <div className="settings-account-hero-copy">
          <span>{planName} account</span>
          <h3>{displayName}</h3>
          <p>
            {PLAN_DESCRIPTIONS[planKey] ||
              PLAN_DESCRIPTIONS.free}
          </p>
        </div>

        <div className="settings-plan-status">
          <BadgeCheck size={18} />
          <span>{subscriptionStatus}</span>
        </div>
      </div>

      <div className="settings-account-summary">
        <div>
          <Mail size={18} />
          <span>Account email</span>
          <strong>{user?.email || '—'}</strong>
        </div>

        <div>
          <CheckCircle2 size={18} />
          <span>Email status</span>
          <strong>
            {emailVerified
              ? 'Verified'
              : 'Verification pending'}
          </strong>
        </div>

        <div>
          <CalendarClock size={18} />
          <span>Member since</span>
          <strong>{formatDate(memberSince)}</strong>
        </div>

        <div>
          <CreditCard size={18} />
          <span>
            {planKey === 'free'
              ? 'Billing status'
              : 'Current period ends'}
          </span>
          <strong>
            {planKey === 'free'
              ? 'No paid subscription'
              : formatDate(periodEnd)}
          </strong>
        </div>
      </div>

      <div className="settings-grid">
        <article className="settings-card">
          <div className="settings-card-icon">
            <RefreshCw size={22} />
          </div>

          <div className="settings-card-copy">
            <span>Account data</span>
            <strong>Refresh your profile</strong>
            <small>
              Synchronize the latest plan, entitlement,
              and billing information.
            </small>
          </div>

          <button
            type="button"
            onClick={refreshProfile}
            disabled={Boolean(busyAction)}
          >
            {busyAction === 'refresh'
              ? 'Refreshing...'
              : 'Refresh account'}
          </button>
        </article>

        <article
          className={`settings-card settings-card-plan settings-card-plan-${planKey}`}
        >
          <div className="settings-card-icon">
            <CreditCard size={22} />
          </div>

          <div className="settings-card-copy">
            <span>Subscription</span>
            <strong>{planName}</strong>
            <small>{subscriptionStatus}</small>
          </div>

          <button
            type="button"
            onClick={openBilling}
            disabled={Boolean(busyAction)}
          >
            {busyAction === 'billing'
              ? 'Opening...'
              : planKey === 'free'
                ? 'Explore plans'
                : 'Manage billing'}
          </button>
        </article>

        <article className="settings-card">
          <div className="settings-card-icon">
            <KeyRound size={22} />
          </div>

          <div className="settings-card-copy">
            <span>Password</span>
            <strong>Secure your account</strong>
            <small>
              Receive a secure password-reset link by email.
            </small>
          </div>

          <button
            type="button"
            onClick={sendPasswordReset}
            disabled={Boolean(busyAction)}
          >
            {busyAction === 'password'
              ? 'Sending...'
              : 'Reset password'}
          </button>
        </article>

        <article className="settings-card settings-card-danger">
          <div className="settings-card-icon">
            <LogOut size={22} />
          </div>

          <div className="settings-card-copy">
            <span>Session</span>
            <strong>Sign out of DiMarket</strong>
            <small>
              End the authenticated session on this device.
            </small>
          </div>

          <button
            type="button"
            onClick={signOut}
            disabled={Boolean(busyAction)}
          >
            {busyAction === 'logout'
              ? 'Signing out...'
              : 'Sign out'}
          </button>
        </article>
      </div>

      <div className="settings-security-note">
        <ShieldCheck size={20} />

        <div>
          <strong>Your account is protected</strong>
          <p>
            Authentication is handled by Supabase, and paid
            subscription changes are completed securely through
            Stripe.
          </p>
        </div>
      </div>

      {message && (
        <div className="settings-message">
          <CheckCircle2 size={18} />
          {message}
        </div>
      )}

      {error && (
        <div className="settings-error">
          <CircleAlert size={18} />
          {error}
        </div>
      )}
    </section>
  )
}

