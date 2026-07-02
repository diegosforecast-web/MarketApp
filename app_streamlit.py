import streamlit as st
import pyrebase
import os
import requests

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

            # Initialize counters
            st.session_state["free_tries"] = 3
            st.session_state["standard_extra_tries"] = 5
            st.session_state["premium_extended_tries"] = 10

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

# TEMP manual assignment
PLAN_USERS = {
    "your@email.com": GOLD
}

plan = PLAN_USERS.get(st.session_state["email"], FREE)

st.title("📊 Market Forecast Dashboard")

# -----------------------------
# SHOW PLAN STATUS
# -----------------------------
if plan == FREE:
    st.warning(f"Free — {st.session_state['free_tries']} tries left")

elif plan == STANDARD:
    st.success(
        f"Standard ($9.99)\nExtra 1–5 day tries left: {st.session_state['standard_extra_tries']}"
    )

elif plan == PREMIUM:
    st.success(
        f"Premium ($17)\nExtended tries left: {st.session_state['premium_extended_tries']}"
    )

elif plan == GOLD:
    st.success("Gold ($49.99) — Unlimited")

# -----------------------------
# STRIPE LINKS
# -----------------------------
STRIPE_STANDARD = "https://buy.stripe.com/test_28E28s2tggOQfyu9EWcwg00"
STRIPE_PREMIUM = "https://buy.stripe.com/test_28EeVe1pc2Y071Y5oGcwg01"
STRIPE_GOLD = "https://buy.stripe.com/test_6oU7sM2tg6acfyucR8cwg02"

# -----------------------------
# UPGRADE UI
# -----------------------------
if plan == FREE:
    st.subheader("Upgrade")
    st.markdown(STRIPE_STANDARD)
    st.markdown(STRIPE_PREMIUM)
    st.markdown(STRIPE_GOLD)

# -----------------------------
# INPUTS
# -----------------------------
tickers = st.multiselect(
    "Tickers",
    ["AAPL", "SPY", "QQQ", "MSFT", "TSLA"],
    max_selections=1 if plan == FREE else None
)

if plan == FREE:
    forecast_days = st.slider("Days (1–5)", 1, 5, 1)

elif plan == STANDARD:
    forecast_days = st.slider("Days", 1, 5, 3)

elif plan == PREMIUM:
    forecast_days = st.slider("Days", 1, 30, 5)

else:
    forecast_days = st.slider("Days", 1, 90, 10)

# -----------------------------
# LIMIT LOGIC (EXACT RULES)
# -----------------------------
def check_limits(days):

    if plan == FREE:
        if st.session_state["free_tries"] <= 0:
            st.error("No free tries left")
            st.stop()

        if days > 5:
            st.error("Free max = 5 days")
            st.stop()

        st.session_state["free_tries"] -= 1


    elif plan == STANDARD:
        # ✅ Unlimited 1–3 days
        if days <= 3:
            return

        # ✅ Only 5 tries for 1–5 days
        if days <= 5:
            if st.session_state["standard_extra_tries"] <= 0:
                st.error("No 1–5 day tries left")
                st.stop()

            st.session_state["standard_extra_tries"] -= 1
        else:
            st.error("Standard max = 5 days")
            st.stop()


    elif plan == PREMIUM:
        # ✅ Unlimited 1–5 days
        if days <= 5:
            return

        # ✅ Only 5 tries 6–30 days
        if days <= 30:
            if st.session_state["premium_extended_tries"] <= 0:
                st.error("No extended tries left")
                st.stop()

            st.session_state["premium_extended_tries"] -= 1
        else:
            st.error("Premium max = 30 days")
            st.stop()


    elif plan == GOLD:
        return


# -----------------------------
# BACKEND CALL
# -----------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "https://market-forecast-prod-133361672503.us-central1.run.app")

def call_api(endpoint, payload):
    try:
        r = requests.post(f"{BACKEND_URL}{endpoint}", json=payload)
        return r.json()
    except:
        st.error("API error")
        return None

# -----------------------------
# RUN FORECAST
# -----------------------------
if st.button("Run Forecast"):

    if not tickers:
        st.error("Select ticker")
        st.stop()

    check_limits(forecast_days)

    data = call_api("/predict", {
        "tickers": tickers,
        "days": forecast_days
    })

    if data:
        st.write(data)
