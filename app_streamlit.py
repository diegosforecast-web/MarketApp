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
        r = requests.get(
            f"{BACKEND_URL}/user-plan",
            params={"email": email}
        )
        return r.json()["plan"]
    except:
        return "free"

plan = get_plan(st.session_state["email"])

# -----------------------------
# HEADER (LOGO + NAME)
# -----------------------------
col1, col2 = st.columns([1, 6])

with col1:
    st.image("logo.png", width=80)

with col2:
    st.markdown("# DiMarket")

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
# INPUTS
# -----------------------------
ticker_input = st.text_input(
    "Enter ticker (e.g. AAPL, TSLA, NVDA)"
)

symbol = ticker_input.strip().upper()

today = date.today()
start = today - timedelta(days=365)
end = today

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
# CALL BACKEND
# -----------------------------
def call_api():
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/v1/compare_models",
            json={
                "symbol": symbol,
                "start": str(start),
                "end": str(end)
            }
        )
        return r.json()
    except:
        st.error("API error")
        return None

# -----------------------------
# RUN
# -----------------------------
if st.button("Run Forecast"):

    if not symbol:
        st.error("Enter a ticker")
        st.stop()

    check_limits(5)

    data = call_api()

    if data:
        st.write(data)
