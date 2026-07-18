from pathlib import Path
from datetime import datetime
import re, shutil

base = Path(r"C:\Dev\MarketApp")
comp = base / "frontend" / "src" / "components"
dash = comp / "Dashboard.jsx"
dash_css = comp / "Dashboard.css"
hist = comp / "PredictionHistory.jsx"
hist_css = comp / "PredictionHistory.css"

def read(p):
    b = p.read_bytes()
    for enc in ("utf-8-sig","utf-16","utf-8"):
        try: return b.decode(enc).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError: pass
    raise RuntimeError(f"Cannot decode {p}")

def write(p,s): p.write_text(s,encoding="utf-8",newline="\n")

def one(s,old,new,label):
    if s.count(old)!=1:
        raise RuntimeError(f"{label}: expected 1 match, found {s.count(old)}")
    return s.replace(old,new,1)

def extract(s,pat,label):
    m=re.search(pat,s,re.S)
    if not m: raise RuntimeError(f"{label} not found")
    return m.group(0), s[:m.start()]+s[m.end():]

stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
for p in (dash,dash_css,hist,hist_css):
    if not p.exists(): raise FileNotFoundError(p)
    shutil.copy2(p,p.with_name(f"{p.name}.{stamp}.bak"))

# PredictionHistory: split list and metrics.
h=read(hist).replace("Ã¢â‚¬â€","â€”").replace("Ã‚Â·","Â·")
h=h.replace(
    "export default function PredictionHistory({ refreshKey = 0 }) {",
    "export default function PredictionHistory({ refreshKey = 0, mode = 'all' }) {",
    1,
)
h=h.replace(
    '<section id="history" className="prediction-history-section">',
    """<section
      id={mode === 'watchlist' ? 'watchlist' : 'performance'}
      className="prediction-history-section"
    >""",
    1,
)
h=h.replace(
    "YOUR AI INVESTING JOURNAL",
    "{mode === 'watchlist' ? 'SAVED FORECASTS' : 'YOUR AI INVESTING JOURNAL'}",
    1,
)
h=h.replace(
    "Prediction Performance",
    "{mode === 'watchlist' ? 'Watchlist' : 'Prediction Performance'}",
    1,
)
h,n=re.subn(
    r'<p className="history-section-description">.*?</p>',
    """<p className="history-section-description">
            {mode === 'watchlist'
              ? 'Review every saved forecast and its transparent progress without rerunning the model.'
              : 'Measure successful predictions, direction accuracy, confidence, and verified performance over time.'}
          </p>""",
    h,count=1,flags=re.S,
)
if n!=1: raise RuntimeError("History description not found")
h=one(
    h,
    '<div className="history-performance-grid">',
    "{mode !== 'watchlist' && (\n      <div className=\"history-performance-grid\">",
    "performance grid",
)
m=re.search(
    r'(<PerformanceMetric\s+icon=\{CalendarClock\}.*?note="Highest verified direction rate"\s*/>\s*</div>)',
    h,re.S,
)
if not m: raise RuntimeError("performance grid end not found")
h=h[:m.start()]+m.group(1)+"\n      )}"+h[m.end():]
h=h.replace(
    """      {!loading &&
        !error &&
        items.length > 0 && (""",
    """      {mode !== 'performance' &&
        !loading &&
        !error &&
        items.length > 0 && (""",
    1,
)
h=h.replace('label="Verified forecasts"','label="Successful predictions"',1)
write(hist,h)

# Dashboard.
d=read(dash).replace("Ã¢â‚¬â€","â€”").replace("Ã‚Â·","Â·")
d=d.replace("import Watchlist from './Watchlist'\n","")
d=d.replace("import './Watchlist.css'\n","")

anchor="  const planName = PLAN_NAMES[planKey] || 'Explorer'\n"
if "visiblePlanCards" not in d:
    d=one(d,anchor,anchor+"""  const planRank = { free: 0, standard: 1, premium: 2, gold: 3 }
  const visiblePlanCards = PLAN_CARDS.filter(
    (plan) => planRank[plan.key] > planRank[planKey],
  )
""","plan filtering")
d=d.replace("{PLAN_CARDS.map((plan) => (","{visiblePlanCards.map((plan) => (",1)

d,n=re.subn(
    r'<div className="sidebar-section-label">.*?</nav>',
    """<div className="sidebar-section-label">
        <span>QUICK ACCESS</span>
        <span className="sidebar-section-arrow" aria-hidden="true">â†“</span>
      </div>

      <nav className="sidebar-navigation">
        <a className="sidebar-link" href="#welcome"><Gift size={19}/>Home</a>
        <a className="sidebar-link sidebar-link-active" href="#forecast"><BrainCircuit size={19}/>AI Forecast</a>
        <a className="sidebar-link" href="#watchlist"><Star size={19}/>Watchlist</a>
        <a className="sidebar-link" href="#portfolio"><BriefcaseBusiness size={19}/>My Portfolio</a>
        <a className="sidebar-link" href="#performance"><BarChart3 size={19}/>AI Journal</a>
        <a className="sidebar-link" href="#journey"><Sparkles size={19}/>Your Journey</a>
        <a className="sidebar-link" href="#community"><MessageSquareText size={19}/>Community</a>
        <a className="sidebar-link" href="#settings"><Settings size={19}/>Settings</a>
        {planKey !== 'gold' && (
          <a className="sidebar-link" href="#plans"><CreditCard size={19}/>Upgrade</a>
        )}
      </nav>""",
    d,count=1,flags=re.S,
)
if n!=1: raise RuntimeError("sidebar block not found")

welcome,d=extract(d,r'<section className="welcome-experience-card">.*?</section>',"welcome")
community,d=extract(d,r'\s*<Community\s*/>',"community")
portfolio,d=extract(d,r'\s*<PortfolioIntelligence\s*/>',"portfolio")
journey,d=extract(d,r'<section id="journey" className="journey-grid">.*?</section>',"journey")
_,d=extract(d,r'\s*<Watchlist\s+onSelectTicker=.*?/>',"legacy watchlist")
forecast,d=extract(d,r'<section id="forecast" className="forecast-workspace">.*?</section>',"forecast")
_,d=extract(d,r'\s*<PredictionHistory refreshKey=\{historyRefreshKey\}/>','history')
trust,d=extract(d,r'<section className="trust-section">.*?</section>',"trust")
settings,d=extract(d,r'\s*<SettingsPanel\s*/>',"settings")
plans,d=extract(d,r'<section id="plans" className="plans-section">.*?</section>',"plans")

welcome="""<section id="welcome" className="welcome-experience-card">
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
      </section>"""

trust=trust.replace('<section className="trust-section">','<section id="standard" className="trust-section">',1)

billing=""
m=re.search(r'\s*\{billingMessage && \(\s*<div className="dashboard-alert">.*?</div>\s*\)\}',d,re.S)
if m:
    billing=m.group(0).strip()
    d=d[:m.start()]+d[m.end():]

ordered=f"""<main className="dimarket-main">
      {welcome}

      {trust}

      {forecast}

      <PredictionHistory mode="watchlist" refreshKey={{historyRefreshKey}}/>

      {portfolio.strip()}

      <PredictionHistory mode="performance" refreshKey={{historyRefreshKey}}/>

      {journey}

      {community.strip()}

      {billing}

      {settings.strip()}

      {{planKey !== 'gold' && (
      {plans}
      )}}"""

d=one(d,'<main className="dimarket-main">',ordered,"main insertion")
write(dash,d)

dc=read(dash_css).replace("`n","\n")+"""

html{scroll-behavior:smooth}
#welcome,#standard,#forecast,#watchlist,#portfolio,#performance,#journey,#community,#settings,#plans{scroll-margin-top:24px}
.welcome-plan-premium{border-color:rgba(192,132,252,.38)}
.welcome-plan-gold{border-color:rgba(250,204,21,.42);background:radial-gradient(circle at 50% 0,rgba(250,204,21,.12),transparent 45%),rgba(3,9,32,.72)}
"""
write(dash_css,dc)
write(hist_css,read(hist_css)+"\n#watchlist,#performance{scroll-margin-top:24px}\n")

print("Phase 1 installed successfully.")
print("Backup timestamp:",stamp)

