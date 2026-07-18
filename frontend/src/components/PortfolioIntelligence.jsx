import { useEffect, useMemo, useState } from 'react'
import {
  BarChart3,
  BrainCircuit,
  BriefcaseBusiness,
  CheckCircle2,
  CircleAlert,
  Gauge,
  LoaderCircle,
  Plus,
  ShieldAlert,
  Sparkles,
  Trash2,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import { supabase } from '../lib/supabase'
import './PortfolioIntelligence.css'

const API_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function money(value) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(Number(value))
}

function percent(value) {
  if (value === null || value === undefined) return '—'
  const number = Number(value)
  return `${number >= 0 ? '+' : ''}${number.toFixed(2)}%`
}

async function authenticatedFetch(path, options = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    throw new Error('Your session has expired. Please sign in again.')
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
          `Request failed (${response.status}).`,
    )
  }

  return payload
}

function ScoreGauge({ value = 0 }) {
  const safe = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div
      className="portfolio-score-gauge"
      style={{ '--portfolio-score': `${safe * 3.6}deg` }}
    >
      <div>
        <strong>{safe.toFixed(0)}</strong>
        <span>/ 100</span>
      </div>
    </div>
  )
}

function AddHoldingForm({ portfolioId, onSaved, onCancel }) {
  const [ticker, setTicker] = useState('')
  const [shares, setShares] = useState('')
  const [averageCost, setAverageCost] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')

    try {
      await authenticatedFetch(
        `/portfolio/${portfolioId}/holdings`,
        {
          method: 'POST',
          body: JSON.stringify({
            ticker: ticker.trim().toUpperCase(),
            shares: shares ? Number(shares) : null,
            average_cost: averageCost
              ? Number(averageCost)
              : null,
          }),
        },
      )
      await onSaved()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="portfolio-add-form" onSubmit={submit}>
      <div className="portfolio-form-heading">
        <div>
          <span className="dashboard-eyebrow">NEW HOLDING</span>
          <h3>Add a stock to your portfolio</h3>
        </div>
        <button type="button" onClick={onCancel}>
          <X size={19} />
        </button>
      </div>

      <div className="portfolio-form-grid">
        <label>
          Ticker
          <input
            value={ticker}
            onChange={(event) =>
              setTicker(event.target.value.toUpperCase())
            }
            placeholder="NVDA"
            maxLength={15}
            required
          />
        </label>

        <label>
          Shares (optional)
          <input
            type="number"
            min="0.0001"
            step="any"
            value={shares}
            onChange={(event) => setShares(event.target.value)}
            placeholder="10"
          />
        </label>

        <label>
          Average cost (optional)
          <input
            type="number"
            min="0"
            step="any"
            value={averageCost}
            onChange={(event) =>
              setAverageCost(event.target.value)
            }
            placeholder="150.00"
          />
        </label>
      </div>

      {error && (
        <div className="portfolio-error">
          <CircleAlert size={18} />
          {error}
        </div>
      )}

      <button className="portfolio-primary-button" disabled={busy}>
        <Plus size={18} />
        {busy ? 'Saving...' : 'Add holding'}
      </button>
    </form>
  )
}

export default function PortfolioIntelligence() {
  const [portfolio, setPortfolio] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [horizon, setHorizon] = useState(3)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')

  async function loadPortfolio() {
    setError('')
    try {
      const payload = await authenticatedFetch('/portfolio/')
      setPortfolio(payload)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPortfolio()
  }, [])

  async function deleteHolding(id) {
    setError('')
    try {
      await authenticatedFetch(`/portfolio/holdings/${id}`, {
        method: 'DELETE',
      })
      setAnalysis(null)
      await loadPortfolio()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function analyzePortfolio() {
    if (!portfolio?.holdings?.length) {
      setError('Add at least one holding before analysis.')
      return
    }

    setAnalyzing(true)
    setError('')

    try {
      const payload = await authenticatedFetch(
        `/portfolio/${portfolio.id}/analyze`,
        {
          method: 'POST',
          body: JSON.stringify({ horizon }),
        },
      )
      setAnalysis(payload)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const allocationData = useMemo(() => {
    if (!analysis?.holdings) return []
    return analysis.holdings
      .filter(
        (item) =>
          item.status === 'analyzed' &&
          Number(item.weight_pct) > 0,
      )
      .map((item) => ({
        name: item.ticker,
        value: Number(item.weight_pct),
      }))
  }, [analysis])

  const recommendationData = useMemo(() => {
    const distribution = analysis?.recommendation_distribution
    if (!distribution) return []
    return Object.entries(distribution).map(([name, value]) => ({
      name,
      value,
    }))
  }, [analysis])

  if (loading) {
    return (
      <section id="portfolio" className="portfolio-intelligence-section">
        <div className="portfolio-loading">
          <LoaderCircle className="portfolio-spinner" size={28} />
          Loading Portfolio Intelligence...
        </div>
      </section>
    )
  }

  return (
    <section id="portfolio" className="portfolio-intelligence-section">
      <div className="section-heading">
        <div>
          <span className="dashboard-eyebrow">
            PORTFOLIO INTELLIGENCE
          </span>
          <h2>{portfolio?.name || 'My Portfolio'}</h2>
        </div>
        <BriefcaseBusiness size={30} />
      </div>

      <div className="portfolio-toolbar">
        <div>
          <p>
            Analyze your holdings together to identify opportunities,
            concentration, and portfolio-level risk.
          </p>
        </div>

        <div className="portfolio-toolbar-actions">
          <select
            value={horizon}
            onChange={(event) =>
              setHorizon(Number(event.target.value))
            }
          >
            {[1, 2, 3, 5].map((days) => (
              <option key={days} value={days}>
                {days}-day analysis
              </option>
            ))}
          </select>

          <button
            type="button"
            className="portfolio-secondary-button"
            onClick={() => setShowForm(true)}
          >
            <Plus size={18} />
            Add holding
          </button>

          <button
            type="button"
            className="portfolio-primary-button"
            onClick={analyzePortfolio}
            disabled={analyzing}
          >
            <BrainCircuit size={18} />
            {analyzing ? 'Analyzing...' : 'Analyze Portfolio'}
          </button>
        </div>
      </div>

      {showForm && (
        <AddHoldingForm
          portfolioId={portfolio.id}
          onCancel={() => setShowForm(false)}
          onSaved={async () => {
            setShowForm(false)
            setAnalysis(null)
            await loadPortfolio()
          }}
        />
      )}

      {error && (
        <div className="portfolio-error">
          <CircleAlert size={19} />
          {error}
        </div>
      )}

      {!portfolio?.holdings?.length && (
        <div className="portfolio-empty">
          <BriefcaseBusiness size={38} />
          <div>
            <h3>Build your first AI-analyzed portfolio.</h3>
            <p>
              Add AAPL, MSFT, NVDA, or any other supported ticker.
            </p>
          </div>
        </div>
      )}

      {portfolio?.holdings?.length > 0 && (
        <div className="portfolio-holdings">
          {portfolio.holdings.map((holding) => (
            <article key={holding.id}>
              <div>
                <strong>{holding.ticker}</strong>
                <span>
                  {holding.shares
                    ? `${Number(holding.shares)} shares`
                    : 'Equal-weight analysis'}
                </span>
              </div>

              <div>
                <span>Average cost</span>
                <strong>{money(holding.average_cost)}</strong>
              </div>

              <button
                type="button"
                onClick={() => deleteHolding(holding.id)}
                aria-label={`Remove ${holding.ticker}`}
              >
                <Trash2 size={18} />
              </button>
            </article>
          ))}
        </div>
      )}

      {analyzing && (
        <div className="portfolio-analyzing">
          <div className="prediction-loader" />
          <div>
            <span className="dashboard-eyebrow">
              ANALYZING PORTFOLIO
            </span>
            <h3>
              DiMarket is evaluating every holding as one system.
            </h3>
            <p>
              Market data · horizon models · opportunity ranking · risk
              aggregation
            </p>
          </div>
        </div>
      )}

      {analysis && !analyzing && (
        <>
          <div className="portfolio-analysis-hero">
            <div className="portfolio-score-panel">
              <ScoreGauge value={analysis.score} />
              <div>
                <span className="dashboard-eyebrow">
                  PORTFOLIO AI SCORE
                </span>
                <h3>
                  {analysis.score >= 75
                    ? 'Strong Opportunity'
                    : analysis.score >= 55
                      ? 'Balanced Outlook'
                      : 'Defensive Outlook'}
                </h3>
                <p>
                  A transparent blend of opportunity, risk,
                  confidence, and diversification.
                </p>
              </div>
            </div>

            <div className="portfolio-kpi-grid">
              <article>
                <TrendingUp size={21} />
                <span>Expected return</span>
                <strong>{percent(analysis.expected_return_pct)}</strong>
              </article>
              <article>
                <Gauge size={21} />
                <span>Average confidence</span>
                <strong>{analysis.average_confidence}%</strong>
              </article>
              <article>
                <Sparkles size={21} />
                <span>Opportunity score</span>
                <strong>{analysis.opportunity_score}</strong>
              </article>
              <article>
                <ShieldAlert size={21} />
                <span>Risk score</span>
                <strong>{analysis.risk_score}</strong>
              </article>
            </div>
          </div>

          <div className="portfolio-opportunity-grid">
            <article className="portfolio-best-card">
              <span className="dashboard-eyebrow">
                BEST OPPORTUNITY
              </span>
              <h3>{analysis.best_opportunity?.ticker || '—'}</h3>
              <strong>
                {analysis.best_opportunity?.recommendation || '—'}
              </strong>
              <p>
                {percent(
                  analysis.best_opportunity?.expected_move_pct,
                )}{' '}
                expected move ·{' '}
                {analysis.best_opportunity?.confidence || 0}% confidence
              </p>
            </article>

            <article className="portfolio-risk-card">
              <span className="dashboard-eyebrow">
                HIGHEST RISK
              </span>
              <h3>{analysis.highest_risk?.ticker || '—'}</h3>
              <strong>
                {analysis.highest_risk?.recommendation || '—'}
              </strong>
              <p>
                {percent(
                  analysis.highest_risk?.expected_move_pct,
                )}{' '}
                expected move ·{' '}
                {analysis.highest_risk?.confidence || 0}% confidence
              </p>
            </article>
          </div>

          <div className="portfolio-chart-grid">
            <article>
              <h3>Allocation</h3>
              {allocationData.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={allocationData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={3}
                    >
                      {allocationData.map((entry, index) => (
                        <Cell key={`${entry.name}-${index}`} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) =>
                        `${Number(value).toFixed(1)}%`
                      }
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p>
                  Add share counts to display market-value allocation.
                </p>
              )}
            </article>

            <article>
              <h3>AI recommendations</h3>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={recommendationData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={3}
                  >
                    {recommendationData.map((entry, index) => (
                      <Cell key={`${entry.name}-${index}`} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </article>
          </div>

          <div className="portfolio-explanation-grid">
            <article>
              <h3>Portfolio strengths</h3>
              <ul>
                {analysis.strengths.map((item) => (
                  <li key={item}>
                    <CheckCircle2 size={17} />
                    {item}
                  </li>
                ))}
                {!analysis.strengths.length && (
                  <li>No major strength detected yet.</li>
                )}
              </ul>
            </article>

            <article>
              <h3>Portfolio risks</h3>
              <ul>
                {analysis.risks.map((item) => (
                  <li key={item}>
                    <CircleAlert size={17} />
                    {item}
                  </li>
                ))}
                {!analysis.risks.length && (
                  <li>No major aggregated risk detected.</li>
                )}
              </ul>
            </article>
          </div>

          <div className="portfolio-ranking">
            <div className="portfolio-ranking-heading">
              <div>
                <span className="dashboard-eyebrow">
                  OPPORTUNITY RANKING
                </span>
                <h3>Every holding, analyzed together</h3>
              </div>
              <BarChart3 size={27} />
            </div>

            <div className="portfolio-ranking-table">
              {analysis.holdings.map((item, index) => (
                <article key={item.holding_id}>
                  <span className="portfolio-rank">#{index + 1}</span>
                  <strong>{item.ticker}</strong>

                  {item.status === 'analyzed' ? (
                    <>
                      <span
                        className={`portfolio-signal portfolio-signal-${String(
                          item.recommendation,
                        ).toLowerCase()}`}
                      >
                        {item.recommendation}
                      </span>
                      <span>{item.confidence}% confidence</span>
                      <span>{percent(item.expected_move_pct)}</span>
                      <span>{item.weight_pct}% weight</span>
                    </>
                  ) : (
                    <span className="portfolio-analysis-failed">
                      Analysis unavailable
                    </span>
                  )}
                </article>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  )
}
