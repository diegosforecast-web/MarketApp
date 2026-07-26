import { useState } from 'react'
import { FlaskConical, RotateCcw } from 'lucide-react'

import { useAuth } from '../contexts/AuthContext'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const STATES = ['free', 'pro', 'expired', 'trial', 'cancelled']
const EVENTS = [
  'new_subscription', 'renewal', 'cancellation', 'expiration',
  'failed_payment', 'trial_expiration', 'downgrade', 'upgrade',
]

export const INTERNAL_TOOLKIT_VISIBLE =
  import.meta.env.DEV &&
  import.meta.env.VITE_ENABLE_INTERNAL_TESTING === 'true'

export default function InternalSubscriptionToolkit() {
  const { user, refreshAccount } = useAuth()
  const [token, setToken] = useState(() => sessionStorage.getItem('dimarket-internal-token') || '')
  const [state, setState] = useState('free')
  const [event, setEvent] = useState('new_subscription')
  const [plan, setPlan] = useState('premium')
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')

  if (!INTERNAL_TOOLKIT_VISIBLE || !user) return null

  async function request(path, body, method = 'POST') {
    setBusy(path)
    setMessage('')
    sessionStorage.setItem('dimarket-internal-token', token)
    try {
      const response = await fetch(`${API_URL}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-DiMarket-Internal-Token': token,
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status}).`)
      await refreshAccount()
      setMessage('Testing state applied. Feature gates refreshed.')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  return (
    <section className="internal-subscription-toolkit" aria-label="Internal subscription testing toolkit">
      <div>
        <FlaskConical size={20} />
        <strong>Internal subscription toolkit</strong>
        <small>Development builds only. State is local and never calls Stripe production APIs.</small>
      </div>

      <label>
        Internal admin token
        <input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" />
      </label>

      <div className="internal-toolkit-row">
        <select value={state} onChange={(e) => setState(e.target.value)}>
          {STATES.map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
        <button disabled={Boolean(busy) || !token} onClick={() => request('/internal/subscriptions/override', { user_id: user.id, state }, 'PUT')}>
          Apply override
        </button>
      </div>

      <div className="internal-toolkit-row">
        <select value={event} onChange={(e) => setEvent(e.target.value)}>
          {EVENTS.map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
        </select>
        <select value={plan} onChange={(e) => setPlan(e.target.value)}>
          {['free', 'standard', 'premium', 'gold'].map((value) => <option key={value}>{value}</option>)}
        </select>
        <button disabled={Boolean(busy) || !token} onClick={() => request('/internal/subscriptions/simulate', { user_id: user.id, event, plan })}>
          Simulate event
        </button>
      </div>

      <button className="internal-toolkit-reset" disabled={Boolean(busy) || !token} onClick={() => request('/internal/subscriptions/reset', { user_id: user.id })}>
        <RotateCcw size={16} /> Reset testing state
      </button>
      {message && <p>{message}</p>}
    </section>
  )
}
