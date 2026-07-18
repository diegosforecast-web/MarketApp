from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

DASHBOARD = Path(r"C:\Dev\MarketApp\frontend\src\components\Dashboard.jsx")
DASHBOARD_CSS = Path(r"C:\Dev\MarketApp\frontend\src\components\Dashboard.css")


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Could not update {label}. Matches found: {count}")
    return updated


def main() -> None:
    for path in (DASHBOARD, DASHBOARD_CSS):
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dashboard_backup = DASHBOARD.with_name(f"{DASHBOARD.name}.{stamp}.bak")
    css_backup = DASHBOARD_CSS.with_name(f"{DASHBOARD_CSS.name}.{stamp}.bak")
    shutil.copy2(DASHBOARD, dashboard_backup)
    shutil.copy2(DASHBOARD_CSS, css_backup)

    dashboard = DASHBOARD.read_text(encoding="utf-8")
    css = DASHBOARD_CSS.read_text(encoding="utf-8")

    if "const [forecastWarning, setForecastWarning]" in dashboard:
        raise RuntimeError(
            "Sprint 5 appears to have already been applied. "
            "No changes were made."
        )

    plan_block = """const PLAN_COPY = {
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
    price: 'Current Stripe price',
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
    price: 'Current Stripe price',
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
]"""

    dashboard = replace_once(
        dashboard,
        r"const PLAN_COPY = \{.*?\}\s*const PLAN_CARDS = \[.*?\n\]",
        plan_block,
        "plan definitions",
    )

    state_line = (
        "  const [showForecastReminder, setShowForecastReminder] = useState(false)"
    )
    if state_line not in dashboard:
        raise RuntimeError("Could not locate showForecastReminder state.")

    dashboard = dashboard.replace(
        state_line,
        state_line
        + "\n  const [forecastWarning, setForecastWarning] = useState(null)",
        1,
    )

    forecast_functions = """  async function executeForecast() {
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

  const positives"""

    dashboard = replace_once(
        dashboard,
        r"  async function runForecast\(event\) \{.*?\n  \}\n\n  const positives",
        forecast_functions,
        "forecast runner",
    )

    reminder_marker = "      {showForecastReminder && prediction && !busy && ("
    if reminder_marker not in dashboard:
        raise RuntimeError("Could not locate forecast reminder block.")

    modal = """      {forecastWarning && (
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

"""
    dashboard = dashboard.replace(reminder_marker, modal + reminder_marker, 1)

    result_marker = "      {prediction && <>\n"
    if result_marker not in dashboard:
        raise RuntimeError("Could not locate prediction results block.")

    banner = """      {prediction && <>
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

"""
    dashboard = dashboard.replace(result_marker, banner, 1)

    renderer = """{PLAN_CARDS.map((plan) => (
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
                  : plan.key === planKey && planKey !== 'free'
                    ? 'Manage billing'
                    : plan.key === planKey
                      ? 'Your current experience'
                      : planKey !== 'free'
                        ? 'Change plan'
                        : 'Choose this experience'}
                <ChevronRight size={17}/>
              </button>
            </article>
          ))}"""

    dashboard = replace_once(
        dashboard,
        r"\{PLAN_CARDS\.map\(\(\[key, name, tagline, features\]\) => \(.*?\)\)\}",
        renderer,
        "plan card renderer",
    )

    css_additions = r"""

/* Sprint 5 Plans */
.forecast-warning-backdrop {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(1, 5, 20, .76);
  padding: 20px;
  backdrop-filter: blur(10px);
}

.forecast-warning-dialog {
  display: grid;
  width: min(100%, 620px);
  grid-template-columns: auto 1fr;
  gap: 18px;
  border: 1px solid rgba(250, 204, 21, .34);
  border-radius: 24px;
  background: rgba(5, 11, 38, .97);
  box-shadow: 0 24px 80px rgba(0, 0, 0, .48);
  padding: 26px;
}

.forecast-warning-icon {
  display: grid;
  width: 54px;
  height: 54px;
  border-radius: 16px;
  background: rgba(250, 204, 21, .11);
  color: #fde68a;
  place-items: center;
}

.forecast-warning-dialog h2 {
  margin: 0;
  color: #fff;
}

.forecast-warning-dialog p {
  margin: 12px 0 0;
  color: #9fbcc5;
  line-height: 1.65;
}

.forecast-warning-actions {
  display: flex;
  grid-column: 1 / -1;
  justify-content: flex-end;
  gap: 10px;
}

.forecast-warning-actions button {
  display: inline-flex;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 13px;
  padding: 0 16px;
  font-weight: 900;
}

.forecast-warning-cancel {
  border: 1px solid rgba(89, 225, 255, .2);
  background: rgba(0, 211, 255, .05);
  color: #b8e8ef;
}

.forecast-warning-confirm {
  border: 0;
  background: linear-gradient(90deg, #00cceb, #873dff);
  color: #fff;
}

.extended-confidence-banner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  border: 1px solid rgba(250, 204, 21, .28);
  border-radius: 20px;
  background: rgba(250, 204, 21, .06);
  padding: 20px 22px;
}

.extended-confidence-banner > svg {
  flex: 0 0 auto;
  color: #fde68a;
}

.extended-confidence-banner strong {
  display: block;
  color: #fff;
}

.extended-confidence-banner p {
  margin: 7px 0 0;
  color: #94b4be;
  line-height: 1.55;
}

.plan-card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
}

.plan-card-heading h3 {
  margin: 0;
}

.plan-card-heading p {
  margin: 7px 0 0;
  color: #93b4be;
}

.plan-price {
  flex: 0 0 auto;
  color: #fff;
  font-size: .96rem;
  text-align: right;
}

.plan-gold .plan-price {
  color: #fde68a;
  font-size: 1.12rem;
}

.plan-access-summary {
  margin-top: 18px;
  border: 1px solid rgba(89, 225, 255, .12);
  border-radius: 13px;
  background: rgba(0, 211, 255, .04);
  color: #b9e3ea;
  padding: 12px;
  font-size: .82rem;
  font-weight: 800;
  line-height: 1.45;
}

@media (max-width: 580px) {
  .forecast-warning-dialog {
    grid-template-columns: 1fr;
  }

  .forecast-warning-actions {
    grid-column: 1;
    flex-direction: column-reverse;
  }

  .forecast-warning-actions button {
    width: 100%;
  }

  .plan-card-heading {
    flex-direction: column;
  }

  .plan-price {
    text-align: left;
  }
}
"""

    if "/* Sprint 5 Plans */" not in css:
        css += css_additions

    DASHBOARD.write_text(dashboard, encoding="utf-8")
    DASHBOARD_CSS.write_text(css, encoding="utf-8")

    print("Sprint 5 applied successfully.")
    print(f"Dashboard backup: {dashboard_backup}")
    print(f"CSS backup: {css_backup}")
    print()
    print("Stripe still requires a new Gold recurring price at $24.99/month.")
    print("Update STRIPE_GOLD_PRICE_ID in the backend .env afterward.")


if __name__ == "__main__":
    main()
