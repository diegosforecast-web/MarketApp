import { useEffect, useState } from 'react'
import { CheckCircle2, CircleAlert, Clock3, LockKeyhole, Sparkles } from 'lucide-react'

import { supabase } from '../lib/supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function selectionLabel(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function backendError(payload, status) {
  const detail = payload?.detail

  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    return detail.message || detail.error || `Daily selection request failed (${status}).`
  }

  return payload?.error || `Daily selection request failed (${status}).`
}

async function authenticatedRequest(method, body) {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    throw new Error('Your session has expired. Please sign in again.')
  }

  const response = await fetch(`${API_URL}/daily-selection/`, {
    method,
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(backendError(payload, response.status))
  }

  return payload
}

export default function PremiumDailySelection() {
  const [selectionState, setSelectionState] = useState(null)
  const [selectedValue, setSelectedValue] = useState('')
  const [selectionBusy, setSelectionBusy] = useState(true)
  const [selectionError, setSelectionError] = useState('')
  const [selectionMessage, setSelectionMessage] = useState('')

  useEffect(() => {
    let active = true

    async function loadSelection() {
      setSelectionBusy(true)
      setSelectionError('')

      try {
        const payload = await authenticatedRequest('GET')
        if (!active) return

        setSelectionState(payload)
        setSelectedValue(payload?.selection || '')
      } catch (requestError) {
        if (!active) return
        setSelectionError(
          requestError.message || 'Unable to load the daily selection.',
        )
      } finally {
        if (active) setSelectionBusy(false)
      }
    }

    loadSelection()

    return () => {
      active = false
    }
  }, [])

  async function submitSelection() {
    if (!selectedValue || selectionBusy || selectionState?.locked === true) return

    setSelectionBusy(true)
    setSelectionError('')
    setSelectionMessage('')

    try {
      const payload = await authenticatedRequest('PUT', {
        selection: selectedValue,
      })

      setSelectionState(payload)
      setSelectedValue(payload?.selection || '')
      setSelectionMessage('Your premium daily selection is confirmed.')
    } catch (requestError) {
      setSelectionError(
        requestError.message || 'Unable to save the daily selection.',
      )
    } finally {
      setSelectionBusy(false)
    }
  }

  const availableSelections = Array.isArray(selectionState?.available_selections)
    ? selectionState.available_selections
    : []
  const locked = selectionState?.locked === true

  return (
    <section className="premium-daily-selection" aria-labelledby="premium-daily-selection-title">
      <div className="premium-daily-selection-heading">
        <div className="premium-daily-selection-icon" aria-hidden="true">
          <Sparkles size={19} />
        </div>
        <div>
          <span>Premium Daily Selection</span>
          <strong id="premium-daily-selection-title">
            {locked ? 'Selection locked for this market day' : 'Choose today’s forecast track'}
          </strong>
        </div>
        {locked && (
          <span className="premium-daily-selection-lock">
            <LockKeyhole size={15} /> Locked
          </span>
        )}
      </div>

      {selectionBusy && !selectionState ? (
        <div className="premium-daily-selection-status" role="status">
          <Clock3 size={18} /> Loading daily selection…
        </div>
      ) : (
        <div className="premium-daily-selection-actions">
          <select
            aria-label="Premium daily selection"
            value={selectedValue}
            onChange={(event) => setSelectedValue(event.target.value)}
            disabled={selectionBusy || locked || availableSelections.length === 0}
          >
            {!selectedValue && <option value="">Select an option</option>}
            {availableSelections.map((selection) => (
              <option key={selection} value={selection}>
                {selectionLabel(selection)}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={submitSelection}
            disabled={selectionBusy || locked || !selectedValue}
          >
            {selectionBusy ? 'Saving…' : locked ? 'Locked' : 'Confirm Selection'}
          </button>
        </div>
      )}

      {selectionState?.market_day && (
        <small>Market day: {selectionState.market_day}</small>
      )}

      {selectionMessage && (
        <div className="premium-daily-selection-feedback success" role="status">
          <CheckCircle2 size={18} /> {selectionMessage}
        </div>
      )}

      {selectionError && (
        <div className="premium-daily-selection-feedback error" role="alert">
          <CircleAlert size={18} /> {selectionError}
        </div>
      )}
    </section>
  )
}
