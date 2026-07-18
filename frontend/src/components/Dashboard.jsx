import { useEffect, useMemo, useState } from 'react'
import {
  Activity, BarChart3, BellRing, BrainCircuit, BriefcaseBusiness, CheckCircle2, ChevronRight,
  CircleAlert, Clock3, CreditCard, Gauge, Gift, History, LogOut, MessageSquareText, Search, Settings, ShieldCheck, Sparkles, Star, TrendingDown,
  TrendingUp, UserCircle2, WandSparkles, X,
} from 'lucide-react'

import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import ForecastTrajectory from './ForecastTrajectory'
import Community from './Community'
import PortfolioIntelligence from './PortfolioIntelligence'
import PredictionHistory from './PredictionHistory'
import './Dashboard.css'
import './PredictionHistory.css'
import './PortfolioIntelligence.css'
import SettingsPanel from './SettingsPanel'
import './SettingsPanel.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const PLAN_NAMES = {
  free: 'Explorer',
  standard: 'Standard',
  premium: 'Premium',
  gold: 'Gold',
}

const PLAN_COPY = {
  free: 'Discover how DiMarket thinks with transparent AI analysis.',
  standard: 'Unlimited 1-3 day forecasts plus three monthly 5-day credits.',
  premium: 'Unlimited 1-5 day forecasts plus three monthly 30-day credits with an extended-horizon warning.',
  gold: 'Unlimited access to every production-supported horizon with clear confidence messaging.',
}

const PLAN_CARDS = [
  {
    key: 'free',
    name: 'Explorer',
    price: 'Free',
    tagline: 'Learn how DiMarket thinks.',
    access: '3 complimentary forecasts - up to 3 trading days',
    features: [
      'Full AI explanation',
      'SHAP driver insights',
      'Historical validation',
      'Risk warnings',
    ],
  },
  {
    key: 'standard',
    name: 'Standard',
    price: '$8.99 / month',
    tagline: 'Trade with greater confidence.',
    access: 'Unlimited 1-3 day forecasts - 3 monthly 5-day credits',
    features: [
      'Advanced explanations',
      'Prediction history',
      'Confidence analytics',
      'Priority processing',
    ],
  },
  {
    key: 'premium',
    name: 'Premium',
    price: '$16.00 / month',
    tagline: 'Professional decision support.',
    access: 'Unlimited 1-5 day forecasts - 3 monthly 30-day credits',
    features: [
      '30-day forecasts include a lower-confidence warning',
      'Historical validation',
      'Stored prediction tracking',
      'PDF reports',
    ],
  },
  {
    key: 'gold',
    name: 'Gold',
    price: '$24.99 / month',
    tagline: 'The complete DiMarket experience.',
    access: 'Unlimited forecasts across every production-supported horizon',
    features: [
      'Extended-horizon confidence messaging',
      'Portfolio intelligence',
      'Scenario analysis',
      'API access',
    ],
  },
]

function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—'
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 2,
  }).format(Number(value))
}

function percent(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—'
  }
  return `${Number(value).toFixed(digits)}%`
}

function tone(value) {
  const normalized = String(value || '').toUpperCase()
  if (normalized === 'BUY') return 'positive'
  if (normalized === 'REJECT' || normalized === 'SELL') return 'negative'
  return 'neutral'
}

function Stars({ count = 3 }) {
  const safeCount = Math.max(0, Math.min(3, Number(count) || 0))
  return <div className="premium-stars">{[0, 1, 2].map((index) => (
    <Star key={index} size={25} fill={index < safeCount ? 'currentColor' : 'none'} />
  ))}</div>
}

function Metric({ icon: Icon, label, value, note, styleName = '' }) {
  return <article className={`metric-card ${styleName}`}>
    <div className="metric-icon"><Icon size={21} /></div>
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  </article>
}

function GaugeCard({ value, level }) {
  const safe = Math.max(0, Math.min(100, Number(value) || 0))
  return <div className="confidence-panel">
    <div className="confidence-gauge" style={{ '--confidence': `${safe * 3.6}deg` }}>
      <div><strong>{Math.round(safe)}%</strong><span>{level}</span></div>
    </div>
    <p>Calibrated production-model confidence.</p>
  </div>
}

export default function Dashboard() {
  const {
    user,
    profile,
    entitlements,
    usageCount,
    applyEntitlements,
    refreshAccount,
  } = useAuth()

  const [ticker, setTicker] = useState('AAPL')
  const [horizon, setHorizon] = useState(1)
  const [prediction, setPrediction] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)
  const [billingBusy, setBillingBusy] = useState('')
  const [billingMessage, setBillingMessage] = useState('')
  const [showForecastReminder, setShowForecastReminder] = useState(false)
  const [forecastWarning, setForecastWarning] = useState(null)
  const [activeSection, setActiveSection] = useState('welcome')

  const planKey = String(entitlements?.plan || profile?.plan || 'free').toLowerCase()
  const planName = PLAN_NAMES[planKey] || 'Explorer'
  const planRank = { free: 0, standard: 1, premium: 2, gold: 3 }
  const visiblePlanCards = planKey === 'free'
    ? PLAN_CARDS
    : PLAN_CARDS.filter(
        (plan) => planRank[plan.key] > planRank[planKey],
      )
  const firstName =
    profile?.full_name ||
    user?.user_metadata?.full_name ||
    user?.email?.split('@')[0] ||
    'Investor'

  const forecastLimit = entitlements?.forecast_limit
  const remaining = entitlements?.forecasts_remaining
  const usageProgress = forecastLimit
    ? Math.min(100, (usageCount / forecastLimit) * 100)
    : 0
  const specialCredit = entitlements?.special_credits?.[0] ?? null
  const supportedHorizons = entitlements?.supported_horizons?.length
    ? entitlements.supported_horizons
    : [1, 2, 3, 5]
  const welcomeStars =
    remaining === null || remaining === undefined
      ? 3
      : Math.min(3, Math.max(0, remaining))

  const sidebarStatus = useMemo(() => {
    if (forecastLimit) return `${remaining ?? 0} tries left`
    if (specialCredit) {
      return `${specialCredit.remaining} ${specialCredit.horizon}-day credits`
    }
    return 'Active'
  }, [forecastLimit, remaining, specialCredit])


  useEffect(() => {
    const sectionIds = [
      'welcome',
      'forecast',
      'watchlist',
      'portfolio',
      'performance',
      'journey',
      'community',
      'account',
      'plans',
    ]

    let animationFrame = null

    function updateActiveSection() {
      animationFrame = null

      const marker = Math.max(
        120,
        window.innerHeight * 0.28,
      )

      let currentSection = sectionIds[0]

      for (const sectionId of sectionIds) {
        const section = document.getElementById(sectionId)

        if (!section) continue

        if (section.getBoundingClientRect().top <= marker) {
          currentSection = sectionId
        } else {
          break
        }
      }

      setActiveSection(currentSection)
    }

    function handleScroll() {
      if (animationFrame !== null) return

      animationFrame =
        window.requestAnimationFrame(updateActiveSection)
    }

    updateActiveSection()

    window.addEventListener('scroll', handleScroll, {
      passive: true,
    })
    window.addEventListener('resize', handleScroll)

    return () => {
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('resize', handleScroll)

      if (animationFrame !== null) {
        window.cancelAnimationFrame(animationFrame)
      }
    }
  }, [prediction, planKey])

  function sidebarClass(sectionId) {
    return `sidebar-link${
      activeSection === sectionId
        ? ' sidebar-link-active'
        : ''
    }`
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const billingStatus = params.get('billing')

    if (!billingStatus) return

    if (billingStatus === 'success') {
      setBillingMessage(
        'Payment completed. DiMarket is activating your plan.',
      )

      let attempts = 0
      const timer = window.setInterval(async () => {
        attempts += 1
        await refreshAccount()

        if (attempts >= 6) {
          window.clearInterval(timer)
          setBillingMessage(
            'Billing is synchronized. Your current plan is shown below.',
          )
        }
      }, 1500)

      window.history.replaceState(
        {},
        document.title,
        window.location.pathname,
      )

      return () => window.clearInterval(timer)
    }

    if (billingStatus === 'cancelled') {
      setBillingMessage(
        'Checkout was cancelled. No subscription change was made.',
      )
    } else if (billingStatus === 'portal-return') {
      setBillingMessage(
        'Welcome back. Your billing changes are being synchronized.',
      )
      refreshAccount()
    }

    window.history.replaceState(
      {},
      document.title,
      window.location.pathname,
    )
  }, [refreshAccount])

  async function billingRequest(path, body) {
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
      body: body ? JSON.stringify(body) : undefined,
    })

    const payload = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(
        payload?.detail ||
          `Billing request failed (${response.status}).`,
      )
    }

    if (!payload?.url) {
      throw new Error('Stripe did not return a redirect URL.')
    }

    window.location.assign(payload.url)
  }

  async function handlePlanAction(targetPlan) {
    if (targetPlan === 'free' && planKey === 'free') return

    setBillingBusy(targetPlan)
    setBillingMessage('')

    try {
      if (planKey !== 'free') {
        await billingRequest('/billing/portal')
        return
      }

      if (targetPlan === 'free') return

      await billingRequest(
        '/billing/checkout',
        { plan: targetPlan },
      )
    } catch (requestError) {
      setBillingMessage(
        requestError.message ||
          'Unable to open Stripe billing.',
      )
      setBillingBusy('')
    }
  }

  async function executeForecast() {
    setBusy(true)
    setError('')

    try {
      const cleanTicker = ticker.trim().toUpperCase()
      if (!cleanTicker) throw new Error('Enter a ticker symbol.')

      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(
        `${API_URL}/forecast/?ticker=${encodeURIComponent(cleanTicker)}&horizon=${horizon}`,
        {
          headers: session?.access_token
            ? { Authorization: `Bearer ${session.access_token}` }
            : {},
        },
      )

      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        const detail = payload?.detail
        const message = typeof detail === 'object' ? detail?.message : detail
        throw new Error(
          message ||
          payload?.error ||
          `Forecast failed (${response.status}).`,
        )
      }

      setPrediction(payload)
      setShowForecastReminder(true)
      applyEntitlements(payload.entitlements)
      setHistoryRefreshKey((value) => value + 1)
    } catch (requestError) {
      setError(requestError.message || 'Unable to run the forecast.')
    } finally {
      setBusy(false)
    }
  }

  function runForecast(event) {
    event.preventDefault()

    if (planKey === 'premium' && Number(horizon) === 30) {
      setForecastWarning({
        title: '30-day forecast confidence notice',
        message:
          'The 30-day forecast is an extended-horizon estimate and generally carries lower confidence than short-term forecasts. DiMarket will show the model confidence clearly with the result.',
      })
      return
    }

    if (planKey === 'gold' && Number(horizon) > 5) {
      setForecastWarning({
        title: `${horizon}-day extended-horizon notice`,
        message:
          'Longer horizons contain more uncertainty than short-term forecasts. Review the displayed confidence, risks, and stored forecast timeline before using this result in a decision.',
      })
      return
    }

    executeForecast()
  }

  function confirmExtendedForecast() {
    setForecastWarning(null)
    executeForecast()
  }

  const positives =
    prediction?.explanation?.top_positive_features?.slice(0, 3) || []
  const negatives =
    prediction?.explanation?.top_negative_features?.slice(0, 3) || []
  const recommendationTone = tone(prediction?.recommendation)
  const recommendationLabel = String(
    prediction?.recommendation || 'HOLD',
  ).toUpperCase()
  const isSellSignal = recommendationLabel === 'SELL'
  const supportiveDrivers = isSellSignal ? negatives : positives
  const opposingDrivers = isSellSignal ? positives : negatives

  return <div className="dimarket-shell">
    <aside className="dimarket-sidebar">
      <div className="sidebar-brand">
        <img src="/logo.png" alt="DiMarket logo" />
        <span>Trustworthy AI Forecasting</span>
      </div>

      <div className="sidebar-section-label">
        <span>QUICK ACCESS</span>
        <span className="sidebar-section-arrow" aria-hidden="true">&darr;</span>
      </div>

      <nav className="sidebar-navigation" aria-label="Dashboard sections">
        <a className={sidebarClass('welcome')} href="#welcome">
          <Gift size={19}/>Home
        </a>
        <a className={sidebarClass('forecast')} href="#forecast">
          <BrainCircuit size={19}/>AI Forecast
        </a>
        <a className={sidebarClass('watchlist')} href="#watchlist">
          <Star size={19}/>Watchlist
        </a>
        <a className={sidebarClass('portfolio')} href="#portfolio">
          <BriefcaseBusiness size={19}/>My Portfolio
        </a>
        <a className={sidebarClass('performance')} href="#performance">
          <BarChart3 size={19}/>AI Journal
        </a>
        <a className={sidebarClass('journey')} href="#journey">
          <Sparkles size={19}/>Your Journey
        </a>
        <a className={sidebarClass('community')} href="#community">
          <MessageSquareText size={19}/>Community
        </a>
        <a className={sidebarClass('account')} href="#account">
          <Settings size={19}/>Account & Settings
        </a>
        {planKey !== 'gold' && (
          <a className={sidebarClass('plans')} href="#plans">
            <CreditCard size={19}/>Upgrade
          </a>
        )}
      </nav>

      <div className="sidebar-account">
        <UserCircle2 size={25}/>
        <div><strong>{firstName}</strong><span>{planName} · {sidebarStatus}</span></div>
      </div>
      <button className="sidebar-logout" type="button" onClick={() => supabase.auth.signOut()}>
        <LogOut size={19}/>Logout
      </button>
    </aside>

    <main className="dimarket-main">
      <section id="welcome" className="welcome-experience-card">
        <div className="welcome-copy">
          <div className="welcome-kicker">
            {planKey === 'free' ? <Gift size={18}/> : <ShieldCheck size={18}/>}
            {planKey === 'free' ? 'WELCOME GIFT' : `${planName.toUpperCase()} EXPERIENCE`}
          </div>
          <h1>Welcome {planKey === 'free' ? 'to DiMarket' : 'back'}, {firstName}.</h1>
          <p>
            {planKey === 'free'
              ? `Your Explorer experience includes ${forecastLimit ?? 3} complimentary forecasts so you can evaluate DiMarket's transparent AI.`
              : planKey === 'standard'
                ? 'Your Standard plan is active with unlimited short-horizon forecasts and monthly 5-day credits.'
                : planKey === 'premium'
                  ? 'Your Premium plan is active with professional forecasting, extended-horizon credits, and transparent prediction tracking.'
                  : 'Your Gold plan is active with unlimited forecasting, Portfolio Intelligence, transparency, and community access.'}
          </p>
          <p className="welcome-philosophy">Markets are uncertain. Decisions do not have to be.</p>
          <a className="welcome-cta" href="#forecast">
            {planKey === 'free' ? 'Start exploring' : 'Run a forecast'}
            <ChevronRight size={18}/>
          </a>
        </div>
        <div className={`welcome-credit-card welcome-plan-${planKey}`}>
          <div className="welcome-credit-icon">
            {planKey === 'free' ? <WandSparkles size={29}/> : <ShieldCheck size={29}/>}
          </div>
          <span>{planKey === 'free' ? 'COMPLIMENTARY EXPERIENCE' : 'CURRENT PLAN'}</span>
          <Stars count={planKey === 'free' ? welcomeStars : 3}/>
          <strong>{planName}</strong>
          <p>
            {forecastLimit
              ? `${remaining ?? 0} complimentary forecasts remaining`
              : specialCredit
                ? `${specialCredit.remaining} ${specialCredit.horizon}-day credits remaining`
                : 'Unlimited production-supported forecasts'}
          </p>
        </div>
      </section>

      <section id="standard" className="trust-section">
        <div className="section-heading">
          <div>
            <span className="dashboard-eyebrow">THE DIMARKET STANDARD</span>
            <h2>Why investors can trust the experience</h2>
          </div>
          <ShieldCheck size={30}/>
        </div>

        <div className="trust-grid">
          {[
            ['Explainable AI', 'Every signal includes its strongest drivers.'],
            ['Historical Validation', 'Performance metrics are shown openly.'],
            ['Confidence Calibration', 'Probability is treated as uncertainty.'],
            ['Production Models', 'Versioned models are loaded from a registry.'],
            ['No Black Box Decisions', 'Reasons and risks are visible together.'],
            ['Honest Limitations', 'Unsupported horizons are rejected.'],
          ].map(([title, description]) => (
            <article key={title}>
              <CheckCircle2 size={21}/>
              <div><strong>{title}</strong><p>{description}</p></div>
            </article>
          ))}
        </div>

        <blockquote>
          DiMarket does not predict the future with certainty. It helps you make
          better decisions with transparent AI.
        </blockquote>
      </section>

      <section id="forecast" className="forecast-workspace">
        <div>
          <span className="dashboard-eyebrow">AI FORECAST</span>
          <h2>Discover one opportunity backed by trustworthy AI.</h2>
          <p>
            Enter a ticker and horizon. DiMarket combines production models,
            calibrated probability, and transparent explanations.
          </p>
        </div>

        <form className="forecast-form" onSubmit={runForecast}>
          <label>
            Ticker
            <div className="forecast-control">
              <Search size={19}/>
              <input
                value={ticker}
                onChange={(event) => setTicker(event.target.value.toUpperCase())}
                maxLength={10}
              />
            </div>
          </label>

          <label>
            Horizon
            <div className="forecast-control">
              <Clock3 size={19}/>
              <select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>
                {supportedHorizons.map((days) => (
                  <option key={days} value={days}>
                    {days} trading {days === 1 ? 'day' : 'days'}
                  </option>
                ))}
              </select>
            </div>
          </label>

          <button className="run-forecast-button" disabled={busy}>
            <BrainCircuit size={20}/>
            {busy ? 'Running AI analysis...' : 'Run AI Forecast'}
            {!busy && <ChevronRight size={18}/>}
          </button>

          {error && <div className="dashboard-alert"><CircleAlert size={20}/>{error}</div>}
        </form>
      </section>

      {!prediction && !busy && (
        <section className="empty-prediction-state">
          <BrainCircuit size={42}/>
          <div>
            <span className="dashboard-eyebrow">READY</span>
            <h2>Your forecast will appear here.</h2>
            <p>Start with AAPL or enter another supported ticker.</p>
          </div>
        </section>
      )}

      {busy && (
        <section className="prediction-loading-card">
          <div className="prediction-loader"/>
          <div>
            <span className="dashboard-eyebrow">ANALYZING</span>
            <h2>DiMarket is evaluating the latest signal.</h2>
            <p>Market structure · indicators · horizon models · confidence calibration</p>
          </div>
        </section>
      )}


      {showForecastReminder && prediction && !busy && (
        <section className="forecast-refresh-reminder" role="status">
          <div className="forecast-refresh-reminder-icon"><BellRing size={22}/></div>
          <div>
            <span className="dashboard-eyebrow">KEEP YOUR FORECAST CURRENT</span>
            <strong>Consider rerunning this forecast each trading day near market open.</strong>
            <p>New closing data, volume, and market conditions may change the outlook. A new forecast does not overwrite the prediction you already saved.</p>
          </div>
          <button type="button" aria-label="Dismiss forecast reminder" onClick={() => setShowForecastReminder(false)}>
            <X size={19}/>
          </button>
        </section>
      )}

      {prediction && <>
        {Number(prediction.horizon) > 5 && (
          <section className="extended-confidence-banner">
            <CircleAlert size={22}/>
            <div>
              <span className="dashboard-eyebrow">
                EXTENDED-HORIZON CONFIDENCE
              </span>
              <strong>
                This {prediction.horizon}-day forecast is{' '}
                {prediction.confidence}% confident.
              </strong>
              <p>
                Longer horizons are more sensitive to changing market
                conditions. Review the confidence level, risks, and
                saved forecast timeline.
              </p>
            </div>
          </section>
        )}

        <section className="prediction-overview">
          <div className="prediction-title-block">
            <div>
              <span className="dashboard-eyebrow">LATEST PREDICTION</span>
              <h2>{prediction.ticker}</h2>
              <p>{prediction.horizon}-day forecast</p>
            </div>
            <div className={`recommendation-badge recommendation-${recommendationTone}`}>
              {recommendationTone === 'positive'
                ? <TrendingUp size={22}/>
                : recommendationTone === 'negative'
                  ? <TrendingDown size={22}/>
                  : <Activity size={22}/>}
              {prediction.recommendation}
            </div>
          </div>

          <div className="prediction-main-grid">
            <div className="prediction-metrics-grid">
              <Metric icon={Activity} label="Current Price" value={money(prediction.current_price)} note="Latest available close"/>
              <Metric icon={TrendingUp} label="Forecast Price" value={money(prediction.forecast_price)} note={`${prediction.horizon}-day estimate`}/>
              <Metric
                icon={Number(prediction.expected_move_pct) >= 0 ? TrendingUp : TrendingDown}
                label="Expected Move"
                value={percent(prediction.expected_move_pct)}
                styleName={Number(prediction.expected_move_pct) >= 0 ? 'metric-positive' : 'metric-negative'}
              />
              <Metric icon={Gauge} label="AI Confidence" value={`${prediction.confidence}%`} note={prediction.confidence_level}/>
            </div>
            <GaugeCard value={prediction.confidence} level={prediction.confidence_level}/>
          </div>
        </section>

        <ForecastTrajectory trajectory={prediction.trajectory} ticker={prediction.ticker}/>

        <section className="decision-grid">
          <article>
            <h3>Supporting evidence</h3>
            <ul>
              {(prediction.reasons || []).map((item) => <li key={item}>{item}</li>)}
              {!prediction.reasons?.length && <li>No supporting reason returned.</li>}
            </ul>
          </article>
          <article>
            <h3>Risks and warnings</h3>
            <ul>
              {(prediction.warnings || []).map((item) => <li key={item}>{item}</li>)}
              {!prediction.warnings?.length && <li>No model warnings returned.</li>}
            </ul>
          </article>
        </section>

        {prediction.explanation && (
          <section className="explanation-section">
            <div className="section-heading">
              <div>
                <span className="dashboard-eyebrow">
                  TRADER BRIEFING
                </span>
                <h2>Why the model reached this decision</h2>
              </div>
              <BrainCircuit size={30}/>
            </div>

            <div className="explanation-briefing-grid">
              <article
                className={`explanation-decision-card explanation-decision-${recommendationTone}`}
              >
                <span>AI decision</span>

                <div>
                  {recommendationTone === 'positive'
                    ? <TrendingUp size={25}/>
                    : recommendationTone === 'negative'
                      ? <TrendingDown size={25}/>
                      : <Activity size={25}/>}
                  <strong>{recommendationLabel}</strong>
                </div>

                <small>
                  {prediction.horizon}-day market outlook
                </small>
              </article>

              <article className="explanation-briefing-metric">
                <span>Confidence</span>
                <strong>{prediction.confidence}%</strong>
                <small>{prediction.confidence_level}</small>
              </article>

              <article className="explanation-briefing-metric">
                <span>Expected move</span>
                <strong
                  className={
                    Number(prediction.expected_move_pct) >= 0
                      ? 'explanation-value-positive'
                      : 'explanation-value-negative'
                  }
                >
                  {percent(prediction.expected_move_pct)}
                </strong>
                <small>
                  Over {prediction.horizon} trading{' '}
                  {Number(prediction.horizon) === 1 ? 'day' : 'days'}
                </small>
              </article>
            </div>

            <div className="explanation-takeaway">
              <BrainCircuit size={21}/>
              <div>
                <span>Bottom line</span>
                <p>{prediction.explanation.summary}</p>
              </div>
            </div>

            <div className="driver-columns explanation-driver-columns">
              <div className="explanation-driver-group explanation-support-group">
                <h3>
                  {isSellSignal
                    ? <TrendingDown size={20}/>
                    : <TrendingUp size={20}/>}
                  What supports this signal
                </h3>

                {supportiveDrivers.map((driver) => (
                  <article className="driver-card" key={driver.feature}>
                    <div className="driver-card-heading">
                      <strong>
                        {driver.display_name || driver.feature}
                      </strong>
                      <span>
                        {Math.abs(
                          Number(driver.impact || 0),
                        ).toFixed(3)}
                      </span>
                    </div>
                    <p>{driver.description}</p>
                  </article>
                ))}

                {!supportiveDrivers.length && (
                  <div className="explanation-empty-driver">
                    No dominant supporting driver was identified.
                  </div>
                )}
              </div>

              <div className="explanation-driver-group explanation-risk-group">
                <h3>
                  {isSellSignal
                    ? <TrendingUp size={20}/>
                    : <TrendingDown size={20}/>}
                  What to watch
                </h3>

                {opposingDrivers.map((driver) => (
                  <article className="driver-card" key={driver.feature}>
                    <div className="driver-card-heading">
                      <strong>
                        {driver.display_name || driver.feature}
                      </strong>
                      <span>
                        {Math.abs(
                          Number(driver.impact || 0),
                        ).toFixed(3)}
                      </span>
                    </div>
                    <p>{driver.description}</p>
                  </article>
                ))}

                {!opposingDrivers.length && (
                  <div className="explanation-empty-driver">
                    No dominant opposing driver was identified.
                  </div>
                )}
              </div>
            </div>

            <div className="explanation-disclaimer">
              <ShieldCheck size={18}/>
              <span>
                SHAP impact values show how strongly each feature
                influenced this model output. They are not expected
                returns or guarantees.
              </span>
            </div>
          </section>
        )}

        {prediction.historical_confidence && (
          <section id="model-validation" className="historical-section">
            <div className="section-heading">
              <div>
                <span className="dashboard-eyebrow">WHY TRUST THIS MODEL</span>
                <h2>Historical validation confidence</h2>
              </div>
              <ShieldCheck size={30}/>
            </div>

            <div className="historical-metrics">
              <Metric icon={Activity} label="Accuracy" value={percent(prediction.historical_confidence.accuracy * 100)}/>
              <Metric icon={TrendingUp} label="Precision" value={percent(prediction.historical_confidence.precision * 100)}/>
              <Metric icon={Gauge} label="F1 Score" value={percent(prediction.historical_confidence.f1 * 100)}/>
              <Metric icon={ShieldCheck} label="AUC" value={percent(prediction.historical_confidence.auc * 100)}/>
            </div>
          </section>
        )}
      </>}

      <PredictionHistory mode="watchlist" refreshKey={historyRefreshKey}/>

      <PortfolioIntelligence />

      <PredictionHistory mode="performance" refreshKey={historyRefreshKey}/>

      <section id="journey" className="journey-grid">
        <article className="journey-card">
          <span className="dashboard-eyebrow">YOUR DIMARKET JOURNEY</span>
          <h2>{planName}</h2>
          <div className="journey-steps">
            <span><CheckCircle2 size={18}/>Account created</span>
            <span><CheckCircle2 size={18}/>Email verified</span>
            <span className={usageCount > 0 ? '' : 'journey-pending'}>
              <CheckCircle2 size={18}/>Generate your first forecast
            </span>
          </div>
          <div className="journey-next">
            <span>Next milestone</span>
            <strong>{usageCount > 0 ? 'Explore another horizon' : 'Run your first forecast'}</strong>
          </div>
        </article>

        <article className="journey-card">
          <span className="dashboard-eyebrow">
            {planKey === 'free' ? 'COMPLIMENTARY USAGE' : 'CURRENT ACCESS'}
          </span>
          <div className="usage-value">
            <strong>{usageCount}</strong>
            <span>{forecastLimit ? `/ ${forecastLimit} forecasts used` : ' forecasts used'}</span>
          </div>
          {forecastLimit && (
            <div className="usage-track">
              <div style={{ width: `${usageProgress}%` }}/>
            </div>
          )}
          <div className="usage-footer">
            <span>
              {forecastLimit
                ? 'Complimentary forecasts remaining'
                : specialCredit
                  ? `${specialCredit.horizon}-day credits remaining`
                  : 'Forecast access'}
            </span>
            <strong>
              {forecastLimit
                ? remaining
                : specialCredit
                  ? specialCredit.remaining
                  : 'Unlimited'}
            </strong>
          </div>
        </article>

        <article className="journey-card">
          <span className="dashboard-eyebrow">CURRENT EXPERIENCE</span>
          <h2>{planName}</h2>
          <p>{PLAN_COPY[planKey] || PLAN_COPY.free}</p>
          <div className="experience-points">
            <span><CheckCircle2 size={16}/>Full AI explanation</span>
            <span><CheckCircle2 size={16}/>Historical validation</span>
            <span><CheckCircle2 size={16}/>Confidence analytics</span>
          </div>
        </article>
      </section>

      <Community />

      <section id="account" className="plans-section account-center-section">
        <div className="section-heading">
          <div>
            <span className="dashboard-eyebrow">ACCOUNT ACCESS</span>
            <h2>Plan, billing, and settings</h2>
          </div>
          <UserCircle2 size={30}/>
        </div>

        <div className="journey-grid account-center-grid">
          <article className="journey-card">
            <span className="dashboard-eyebrow">CURRENT PLAN</span>
            <h2>{planName}</h2>
            <p>{PLAN_COPY[planKey] || PLAN_COPY.free}</p>
            <div className="experience-points">
              <span><CheckCircle2 size={16}/>Subscription status: {entitlements?.subscription_status || 'active'}</span>
              <span><CheckCircle2 size={16}/>Account: {user?.email || 'Signed in'}</span>
              <span><CheckCircle2 size={16}/>Forecast access: {sidebarStatus}</span>
            </div>

            {planKey === 'free' ? (
              <a className="welcome-cta" href="#plans">
                View available plans
                <ChevronRight size={18}/>
              </a>
            ) : (
              <button
                type="button"
                className="welcome-cta"
                disabled={Boolean(billingBusy)}
                onClick={() => handlePlanAction(planKey)}
              >
                <CreditCard size={18}/>
                {billingBusy === planKey ? 'Opening Stripe...' : 'Manage billing'}
              </button>
            )}
          </article>

          <article className="journey-card">
            <span className="dashboard-eyebrow">ACCOUNT SECURITY</span>
            <h2>Signed in and protected</h2>
            <p>
              Manage your personal preferences below. Billing changes are handled
              securely through Stripe.
            </p>
            <div className="experience-points">
              <span><ShieldCheck size={16}/>Authenticated account</span>
              <span><ShieldCheck size={16}/>Secure billing portal</span>
              <span><ShieldCheck size={16}/>Private prediction history</span>
            </div>
          </article>
        </div>

        {billingMessage && (
          <div className="dashboard-alert">
            <CreditCard size={20}/>
            {billingMessage}
          </div>
        )}
      </section>

      <SettingsPanel />

      {planKey !== 'gold' && (
      <section id="plans" className="plans-section">
        <div className="section-heading">
          <div>
            <span className="dashboard-eyebrow">CONTINUE YOUR JOURNEY</span>
            <h2>Choose the experience that fits your ambition</h2>
          </div>
          <Sparkles size={30}/>
        </div>

        <div className="plan-grid">
          {visiblePlanCards.map((plan) => (
            <article
              key={plan.key}
              className={`plan-card plan-${plan.key} ${
                plan.key === planKey ? 'plan-current' : ''
              }`}
            >
              {plan.key === planKey && (
                <span className="current-plan-label">
                  CURRENT EXPERIENCE
                </span>
              )}

              <div className="plan-card-heading">
                <div>
                  <h3>{plan.name}</h3>
                  <p>{plan.tagline}</p>
                </div>
                <strong className="plan-price">{plan.price}</strong>
              </div>

              <div className="plan-access-summary">
                {plan.access}
              </div>

              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>
                    <CheckCircle2 size={16}/>
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                type="button"
                disabled={
                  Boolean(billingBusy) ||
                  (plan.key === 'free' && planKey === 'free')
                }
                onClick={() => handlePlanAction(plan.key)}
              >
                {billingBusy === plan.key
                  ? 'Opening Stripe...'
                  : plan.key === planKey
                    ? 'Your current experience'
                    : planKey !== 'free'
                      ? 'Change plan'
                      : 'Choose this experience'}
                <ChevronRight size={17}/>
              </button>
            </article>
          ))}
        </div>
      </section>
      )}

      

      {forecastWarning && (
        <div className="forecast-warning-backdrop">
          <section
            className="forecast-warning-dialog"
            role="dialog"
            aria-modal="true"
          >
            <div className="forecast-warning-icon">
              <CircleAlert size={28}/>
            </div>

            <div>
              <span className="dashboard-eyebrow">CONFIDENCE NOTICE</span>
              <h2>{forecastWarning.title}</h2>
              <p>{forecastWarning.message}</p>
            </div>

            <div className="forecast-warning-actions">
              <button
                type="button"
                className="forecast-warning-cancel"
                onClick={() => setForecastWarning(null)}
              >
                Cancel
              </button>

              <button
                type="button"
                className="forecast-warning-confirm"
                onClick={confirmExtendedForecast}
              >
                Continue with forecast
                <ChevronRight size={17}/>
              </button>
            </div>
          </section>
        </div>
      )}
      
    </main>
  </div>
}

