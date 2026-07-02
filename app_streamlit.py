import streamlit as st
import pyrebase
import os
import requests
from datetime import date, timedelta

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="DiMarket", layout="wide")

# -----------------------------
# FIREBASE
# -----------------------------
firebase_config = {
    "apiKey": "AIzaSyAQjWc74RTNi4x9ZySMOZZw1fbF3TIjsRk",
    "authDomain": "diego-market-forecast.firebaseapp.com",
    "projectId": "diego-market-forecast",
    "storageBucket": "diego-market-forecast.firebasestorage.app",
    "messagingSenderId": "133361672503",
    "appId": "1:133361672503:web:18dc7766a082d340663ab2",
    "databaseURL": ""
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# -----------------------------
# LOGIN (FIXED — FORM)
# -----------------------------
if "user" not in st.session_state:
    st.title("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user"] = user
            st.session_state["email"] = email
            st.session_state["free_tries"] = 3
            st.session_state["standard_extra_tries"] = 5
            st.session_state["premium_extended_tries"] = 10
            st.rerun()
        except:
            st.error("Login failed")

    st.stop()

# -----------------------------
# BACKEND
# -----------------------------
BACKEND_URL = "https://YOUR_CLOUD_RUN_URL"

def get_plan(email):
    try:
        r = requests.get(f"{BACKEND_URL}/user-plan", params={"email": email})
        return r.json().get("plan", "free")
    except:
        return "free"

plan = get_plan(st.session_state["email"])

# -----------------------------
# NEON THEME CSS
# -----------------------------
st.markdown(
    """
    <style>
        body {
            background-color: #0A0F1F;
            color: #E0E0E0;
        }
        .sidebar .sidebar-content {
            background-color: #0A0F1F;
            border-right: 2px solid #00FFFF;
        }
        .sidebar .sidebar-content a {
            color: #00FFFF !important;
            font-weight: 600;
        }
        .app-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .app-title {
            font-size: 42px;
            font-weight: 700;
            color: #00FFFF;
            text-shadow: 0 0 10px #9D00FF, 0 0 20px #00FFFF;
            margin-top: -10px;
        }
        .divider {
            width: 100%;
            height: 1px;
            background-color: #00FFFF;
            box-shadow: 0 0 10px #00FFFF;
            margin-top: 10px;
            margin-bottom: 20px;
        }
        .stButton>button {
            background-color: #0A0F1F;
            color: #00FFFF;
            border: 1px solid #00FFFF;
            border-radius: 8px;
            font-weight: 600;
            box-shadow: 0 0 10px #00FFFF;
        }
        .stButton>button:hover {
            background-color: #9D00FF;
            color: white;
            box-shadow: 0 0 20px #9D00FF;
        }
        .stTextInput>div>div>input {
            background-color: #111;
            color: #E0E0E0;
            border: 1px solid #00FFFF;
            border-radius: 6px;
        }
        .stTextInput>div>div>input:focus {
            border-color: #9D00FF;
            box-shadow: 0 0 10px #9D00FF;
        }
        .stSelectbox>div>div>select {
            background-color: #111;
            color: #E0E0E0;
            border: 1px solid #00FFFF;
            border-radius: 6px;
        }
        .stMultiSelect>div>div>div {
            background-color: #111;
            color: #E0E0E0;
            border: 1px solid #00FFFF;
            border-radius: 6px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# SIDEBAR NAVIGATION
# -----------------------------
st.sidebar.markdown(
    """
    <style>
        .sidebar-title {
            font-size: 24px;
            font-weight: 700;
            color: #00FFFF;
            text-align: center;
            margin-bottom: 20px;
        }
        .sidebar-item {
            font-size: 18px;
            color: #9D00FF;
            margin-bottom: 10px;
        }
        .sidebar-item:hover {
            color: #00FFFF;
            text-shadow: 0 0 10px #00FFFF;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown('<div class="sidebar-title">⚡ DiMarket</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-item">🏠 Home</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-item">🤖 AI Forecast</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-item">💰 Pricing Plans</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-item">👤 My Account</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-item">🚪 Logout</div>', unsafe_allow_html=True)

# -----------------------------
# HEADER (LOGO + TITLE)
# -----------------------------
st.markdown('<div class="app-header">', unsafe_allow_html=True)

if os.path.exists("logo.png"):
    st.image("logo.png", width=250)
else:
    st.write("")

st.markdown('<div class="app-title">DiMarket</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# -----------------------------
# PLAN STATUS
# -----------------------------
if plan == "free":
    st.warning(f"Free — {st.session_state['free_tries']} tries left")

elif plan == "standard":
    st.success(f"Standard ✅ | Extra tries: {st.session_state['standard_extra_tries']}")

elif plan == "premium":
    st.success(f"Premium ✅ | Extended tries: {st.session_state['premium_extended_tries']}")

elif plan == "gold":
    st.success("Gold ✅ Unlimited")

# -----------------------------
# STRIPE LINKS
# -----------------------------
STRIPE_STANDARD = "https://buy.stripe.com/test_28E28s2tggOQfyu9EWcwg00"
STRIPE_PREMIUM = "https://buy.stripe.com/test_28EeVe1pc2Y071Y5oGcwg01"
STRIPE_GOLD = "https://buy.stripe.com/test_6oU7sM2tg6acfyucR8cwg02"

# -----------------------------
# PRICING UI
# -----------------------------
st.subheader("🚀 Choose your plan")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("### 🆓 Free")
    st.write("• 3 tries")
    st.write("• 1–5 days")
    st.write("• 1 ticker")
    if plan == "free":
        st.success("Current")

with c2:
    st.markdown("### 💵 Standard")
    st.write("$9.99 / month")
    st.write("• Unlimited 1–3 days")
    st.write("• 5 tries (1–5 days)")
    if plan == "standard":
        st.success("Your plan")
    else:
        if st.button("Upgrade Standard"):
            st.markdown(STRIPE_STANDARD)

with c3:
    st.markdown("### 💎 Premium")
    st.write("$17 / month")
    st.write("• Unlimited 1–5 days")
    st.write("• 10 tries (6–30)")
    if plan == "premium":
        st.success("Your plan")
    else:
        if st.button("Upgrade Premium"):
            st.markdown(STRIPE_PREMIUM)

with c4:
    st.markdown("### 🔥 Gold")
    st.write("$49.99 / month")
    st.write("• Unlimited everything")
    if plan == "gold":
        st.success("Your plan")
    else:
        if st.button("Upgrade Gold"):
            st.markdown(STRIPE_GOLD)

# -----------------------------
# TICKER INPUT (MULTI + MANUAL + DAYS SELECTOR)
# -----------------------------
ALL_TICKERS = [
    "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOGL", "SPY", "QQQ",
    "RKLB", "NFLX", "AMD", "PLTR", "BABA", "COIN", "INTC"
]

st.subheader("📈 Forecast Input")

with st.form("ticker_form"):
    selected = st.multiselect("Choose tickers", ALL_TICKERS)
    typed = st.text_input("Or type a ticker (comma-separated allowed)")

    # Days selector based on plan
    if plan == "free":
        days = st.selectbox("Select forecast days", [1, 2, 3, 4, 5])
    elif plan == "standard":
        days = st.selectbox("Select forecast days", [1, 2, 3])
    elif plan == "premium":
        days = st.selectbox("Select forecast days", list(range(1, 6)))
    elif plan == "gold":
        days = st.selectbox("Select forecast days", list(range(1, 31)))

    submitted = st.form_submit_button("Run Forecast")

typed_list = []
if typed:
    typed_list = [t.strip().upper() for t in typed.split(",") if t.strip()]

tickers_final = sorted(set(selected + typed_list))

# -----------------------------
# LIMIT LOGIC
# -----------------------------
def check_limits(days):
    if plan == "free":
        if st.session_state["free_tries"] <= 0:
            st.error("No tries left")
            st.stop()
        st.session_state["free_tries"] -= 1

    elif plan == "standard":
        if days > 3:
            if st.session_state["standard_extra_tries"] <= 0:
                st.error("No extra tries")
                st.stop()
            st.session_state["standard_extra_tries"] -= 1

    elif plan == "premium":
        if days > 5:
            if st.session_state["premium_extended_tries"] <= 0:
                st.error("No extended tries")
                st.stop()
            st.session_state["premium_extended_tries"] -= 1

# -----------------------------
# BACKEND CALL
# -----------------------------
def call_api(symbol, start, end):
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/v1/compare_models",
            json={
                "symbol": symbol,
                "start": str(start),
                "end": str(end),
                "days": days
            }
        )
        return r.json()
    except:
        st.error("API error")
        return None

# -----------------------------
# RUN FORECAST
# -----------------------------
today = date.today()
start = today - timedelta(days=365)
end = today

if submitted:

    if not tickers_final:
        st.error("Enter or select a ticker")
        st.stop()

    check_limits(days)

    for symbol in tickers_final:
        st.write(f"### {symbol}")
        data = call_api(symbol, start, end)
        if data:
            st.write(data)
