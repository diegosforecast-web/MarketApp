import streamlit as st
import pyrebase
import os
import requests

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Market Forecast Dashboard", layout="wide")

# -----------------------------
# FIREBASE CONFIG
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

            # Free limits
            st.session_state["free_tries"] = 3
            st.session_state["standard_extra_tries"] = 5
            st.session_state["premium_extended_tries"] = 10

            st.rerun()
        except:
            st.error("Login failed")

    st.stop()

# -----------------------------
# BACKEND CONFIG
# -----------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "https://market-forecast-prod-133361672503.us-central1.run.app")

def get_plan(email):
    try:
        resp = requests.get(
            f"{BACKEND_URL}/user-plan",
            params={"email": email}
        )
        return resp.json()["plan"]
    except:
        return "free"

plan = get_plan(st.session_state["email"])

# -----------------------------
# TITLE
# -----------------------------
st.title("📊 Market Forecast Dashboard")

# -----------------------------
# PLAN STATUS
# -----------------------------
if plan == "free":
    st.warning(f"Free — {st.session_state['free_tries']} tries left")

elif plan == "standard":
    st.success(f"Standard ✅ | Extra tries left: {st.session_state['standard_extra_tries']}")

elif plan == "premium":
    st.success(f"Premium ✅ | Extended tries left: {st.session_state['premium_extended_tries']}")

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

col1, col2, col3, col4 = st.columns(4)

# FREE
with col1:
    st.markdown("### 🆓 Free")
    st.write("• 3 total tries")
    st.write("• 1 ticker")
    st.write("• 1–5 days")
    if plan == "free":
        st.success("Current plan")

# STANDARD
with col2:
    st.markdown("### 💵 Standard")
    st.write("$9.99/month")
    st.write("• Unlimited 1–3 days")
    st.write("• 5 tries (1–5 days)")
    st.write("• Multiple tickers")
    if plan == "standard":
        st.success("Your plan ✅")
    else:
        if st.button("Upgrade Standard"):
            st.markdown(STRIPE_STANDARD)

# PREMIUM
with col3:
    st.markdown("### 💎 Premium")
    st.write("$17/month")
    st.write("• Unlimited 1–5 days")
    st.write("• 10 tries (6–30 days)")
    st.write("• Multiple tickers")
    if plan == "premium":
        st.success("Your plan ✅")
    else:
        if st.button("Upgrade Premium"):
            st.markdown(STRIPE_PREMIUM)

# GOLD
with col4:
    st.markdown("### 🔥 Gold")
    st.write("$49.99/month")
    st.write("• Unlimited everything")
    if plan == "gold":
        st.success("Your plan ✅")
    else:
        if st.button("Upgrade Gold"):
            st.markdown(STRIPE_GOLD)

# -----------------------------
# INPUTS
# -----------------------------
tickers = st.multiselect(
    "Tickers",
    ["AAPL", "SPY", "QQQ", "MSFT", "TSLA"],
    max_selections=1 if plan == "free" else None
)

if plan == "free":
    forecast_days = st.slider("Days", 1, 5, 1)

elif plan == "standard":
    forecast_days = st.slider("Days", 1, 5, 3)

elif plan == "premium":
    forecast_days = st.slider("Days", 1, 30, 5)

else:
    forecast_days = st.slider("Days", 1, 90, 10)

# -----------------------------
# LIMIT LOGIC
# -----------------------------
def check_limits(days):

    if plan == "free":
        if st.session_state["free_tries"] <= 0:
            st.error("No free tries left")
            st.stop()
        st.session_state["free_tries"] -= 1

    elif plan == "standard":
        if days > 3:
            if st.session_state["standard_extra_tries"] <= 0:
                st.error("No extended tries left")
                st.stop()
            st.session_state["standard_extra_tries"] -= 1

    elif plan == "premium":
        if days > 5:
            if st.session_state["premium_extended_tries"] <= 0:
                st.error("No extended tries left")
                st.stop()
            st.session_state["premium_extended_tries"] -= 1

# -----------------------------
# CALL BACKEND
# -----------------------------
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

    data = call_api("/api/v1/predict", {
        "tickers": tickers,
        "days": forecast_days
    })

    if data:
        st.write(data)
