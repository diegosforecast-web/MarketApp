import { useCallback, useEffect, useState } from 'react'
import {
  ArrowRight,
  CircleAlert,
  LoaderCircle,
  Plus,
  Star,
  Trash2,
} from 'lucide-react'

import { supabase } from '../lib/supabase'
import './Watchlist.css'

const API_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function authenticatedFetch(path, options = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    throw new Error(
      'Your session has expired. Please sign in again.',
    )
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
      ...(options.headers || {}),
    },
  })

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = payload?.detail

    throw new Error(
      typeof detail === 'string'
        ? detail
        : detail?.message ||
          `Watchlist request failed (${response.status}).`,
    )
  }

  return payload
}

export default function Watchlist({ onSelectTicker }) {
  const [items, setItems] = useState([])
  const [ticker, setTicker] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyTicker, setBusyTicker] = useState('')
  const [error, setError] = useState('')

  const loadWatchlist = useCallback(async () => {
    setError('')

    try {
      const payload = await authenticatedFetch('/watchlist/')
      setItems(payload?.items || [])
    } catch (requestError) {
      setError(
        requestError.message ||
          'Unable to load the watchlist.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadWatchlist()
  }, [loadWatchlist])

  async function addTicker(event) {
    event.preventDefault()

    const normalized = ticker.trim().toUpperCase()

    if (!normalized) {
      setError('Enter a ticker symbol.')
      return
    }

    setBusyTicker(normalized)
    setError('')

    try {
      await authenticatedFetch('/watchlist/', {
        method: 'POST',
        body: JSON.stringify({
          ticker: normalized,
        }),
      })

      setTicker('')
      await loadWatchlist()
    } catch (requestError) {
      setError(
        requestError.message ||
          'Unable to add the ticker.',
      )
    } finally {
      setBusyTicker('')
    }
  }

  async function removeTicker(symbol) {
    setBusyTicker(symbol)
    setError('')

    try {
      await authenticatedFetch(
        `/watchlist/${encodeURIComponent(symbol)}`,
        {
          method: 'DELETE',
        },
      )

      await loadWatchlist()
    } catch (requestError) {
      setError(
        requestError.message ||
          'Unable to remove the ticker.',
      )
    } finally {
      setBusyTicker('')
    }
  }

  function selectTicker(symbol) {
    onSelectTicker?.(symbol)
  }

  return (
    <section id="watchlist" className="watchlist-section">
      <div className="section-heading watchlist-heading">
        <div>
          <span className="dashboard-eyebrow">
            QUICK ACCESS
          </span>
          <h2>Your Watchlist</h2>
          <p>
            Save the tickers you follow and move directly into a
            transparent DiMarket forecast.
          </p>
        </div>
        <Star size={30}/>
      </div>

      <form
        className="watchlist-add-form"
        onSubmit={addTicker}
      >
        <label>
          Add ticker
          <input
            value={ticker}
            onChange={(event) =>
              setTicker(event.target.value.toUpperCase())
            }
            placeholder="AAPL"
            maxLength={15}
          />
        </label>

        <button
          type="submit"
          disabled={Boolean(busyTicker)}
        >
          <Plus size={18}/>
          {busyTicker ? 'Saving...' : 'Add to watchlist'}
        </button>
      </form>

      {error && (
        <div className="watchlist-error">
          <CircleAlert size={18}/>
          {error}
        </div>
      )}

      {loading && (
        <div className="watchlist-state">
          <LoaderCircle
            className="watchlist-spinner"
            size={26}
          />
          Loading your watchlist...
        </div>
      )}

      {!loading && !items.length && (
        <div className="watchlist-state">
          <Star size={28}/>
          Your saved tickers will appear here.
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="watchlist-grid">
          {items.map((item) => (
            <article key={item.id}>
              <div className="watchlist-symbol">
                <Star size={19}/>
                <strong>{item.ticker}</strong>
              </div>

              <div className="watchlist-actions">
                <button
                  type="button"
                  className="watchlist-forecast-button"
                  onClick={() => selectTicker(item.ticker)}
                >
                  Forecast
                  <ArrowRight size={17}/>
                </button>

                <button
                  type="button"
                  className="watchlist-remove-button"
                  aria-label={`Remove ${item.ticker}`}
                  disabled={busyTicker === item.ticker}
                  onClick={() => removeTicker(item.ticker)}
                >
                  <Trash2 size={17}/>
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
