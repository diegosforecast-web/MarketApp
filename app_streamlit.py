import streamlit as st
import pyrebase
import os
import requests
import plotly.graph_objects as go

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Market Forecast Dashboard", layout="wide")

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
# LOGIN
# -----------------------------
if "user" not in st.session_state:
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user"] = user
            st.session_state["email"] = email
            st.session_state["tries_left"] = 3
            st.session_state["premium_tries"] = 5
            st.rerun()
        except:
            st.error("Login failed")

    st.stop()

# -----------------------------
# PLANS
# -----------------------------
FREE = "free"
STANDARD = "standard"
PREMIUM = "premium"
GOLD = "gold"

# 👉 TEMP manual assignment (you can change emails here)
PLAN_USERS = {
    "your@email.com": GOLD
}

plan = PLAN_USERS.get(st.session_state["email"], FREE)

st.title("📊 Market Forecast Dashboard")

# -----------------------------
# SHOW PLAN
# -----------------------------
if plan == FREE:
    st.warning(f"🆓 Free plan — {st.session_state['tries_left']} tries left")
elif plan == STANDARD:
    st.success("✅ Standard plan ($9.99)")
elif plan == PREMIUM:
    st.success(f"✅ Premium plan — {st.session_state['premium_tries']} monthly tries left")
elif plan == GOLD:
    st.success("🔥 Gold plan — unlimited")

# -----------------------------
# STRIPE LINKS (✅ YOUR LINKS)
# -----------------------------
STRIPE_STANDARD = "https://buy.stripe.com/test_28E28s2tggOQfyu9EWcwg00"
STRIPE_PREMIUM = "https://buy.stripe.com/test_28EeVe1pc2Y071Y5oGcwg01"
STRIPE_GOLD = "https://buy.stripe.com/test_6oU7sM2tg6acfyucR8cwg02"

# -----------------------------
# UPGRADE UI
# -----------------------------
if plan == FREE:
    st.subheader("🚀 Upgrade your plan")
    st.markdown(f"{STRIPE_STANDARD}")
    st.markdown(f"{STRIPE_PREMIUM}")
    st.markdown(f"{STRIPE_GOLD}")

# -----------------------------
# LIMIT LOGIC
# -----------------------------
def check_limits(days):
    global plan

    if plan == FREE:
        if st.session_state["tries_left"] <= 0:
            st.error("❌ No free tries left")
            st.stop()

        if days > 5:
            st.error("Free plan max 5 days")
            st.stop()

        st.session_state["tries_left"] -= 1

    elif plan == STANDARD:
        if days > 5:
            st.error("Standard: max 5 days (only 5 special tries allowed)")
            st.stop()

    elif plan == PREMIUM:
        if days > 5:
            if st.session_state["premium_tries"] <= 0:
                st.error("❌ No Premium extended tries left")
                st.stop()
            st.session_state["premium_tries"] -= 1

    elif plan == GOLD:
        return

# -----------------------------
# INPUTS
# -----------------------------
tickers = st.multiselect(
    "Tickers",
    ["AAPL", "SPY", "QQQ", "MSFT", "TSLA"],
    max_selections=1 if plan == FREE else None
)

if plan == FREE:
    forecast_days = st.slider("Forecast days (1–5)", 1, 5, 1)

elif plan == STANDARD:
    forecast_days = st.slider("Forecast days", 1, 5, 2)

elif plan == PREMIUM:
    forecast_days = st.slider("Forecast days", 1, 30, 5)

else:
    forecast_days = st.slider("Forecast days", 1, 90, 10)

# -----------------------------
# BACKEND
# -----------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "https://YOUR_CLOUD_RUN_URL")

def call_api(endpoint, payload):
    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", json=payload)
        return resp.json()
    except:
        st.error("API error")
        return None

# -----------------------------
# RUN FORECAST
# -----------------------------
if st.button("Run Forecast"):
    if not tickers:
        st.error("Select at least one ticker")
        st.stop()

    check_limits(forecast_days)

    data = call_api("/predict", {
        "tickers": tickers,
        "days": forecast_days
    })

    if data:
        st.write(data)
