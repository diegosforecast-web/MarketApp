import streamlit as st
import pyrebase
import os
import requests
import plotly.graph_objects as go

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
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# -----------------------------
# LOGIN UI
# -----------------------------
st.title("📊 Market Forecast Dashboard")

if "user" not in st.session_state:
    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user"] = user
            st.success("✅ Logged in")
            st.rerun()
        except:
            st.error("❌ Login failed")

    st.stop()


# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Market Forecast Dashboard", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "https://YOUR_CLOUD_RUN_URL")  # <-- set this


# -----------------------------
# HELPERS
# -----------------------------
def call_api(endpoint, payload, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", json=payload, headers=headers)
        if resp.status_code != 200:
            return None, f"{resp.status_code}: {resp.text}"
        return resp.json(), None
    except Exception as e:
        return None, str(e)


def get_api(endpoint, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)
        if resp.status_code != 200:
            return None, f"{resp.status_code}: {resp.text}"
        return resp.json(), None
    except Exception as e:
        return None, str(e)


def trend_emoji(trend: str | None):
    if not trend:
        return "➖"
    t = trend.lower()
    if "up" in t or "bull" in t:
        return "⬆️"
    if "down" in t or "bear" in t:
        return "⬇️"
    return "➡️"


def show_confidence_chart(symbol: str, pred: dict):
    y_pred = pred.get("prediction")
    if y_pred is None:
        return

    ci_low = pred.get("ci_low")
    ci_high = pred.get("ci_high")

    # fallback if backend doesn’t send explicit CI
    if ci_low is None or ci_high is None:
        conf = pred.get("confidence", 0.7)
        vol = pred.get("volatility", 0.02)
        spread = max(vol * y_pred, 0.5)
        ci_low = y_pred - spread
        ci_high = y_pred + spread

    x = ["CI Low", "Prediction", "CI High"]
    y = [ci_low, y_pred, ci_high]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        line=dict(color="royalblue"),
        fill="tonexty",
        name=symbol,
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def show_prediction_card(symbol: str, pred: dict, horizon_label: str):
    st.subheader(f"{symbol} {horizon_label}")

    col1, col2, col3, col4 = st.columns(4)

    price = pred.get("prediction")
    ts = pred.get("timestamp")
    conf = pred.get("confidence")
    vol = pred.get("volatility")
    trend = pred.get("trend")

    with col1:
        if price is not None:
            st.metric("Predicted Price", f"${price:.2f}")
        else:
            st.metric("Predicted Price", "N/A")

    with col2:
        st.metric("Trend", trend_emoji(trend), trend or "unknown")

    with col3:
        if conf is not None:
            st.metric("Confidence", f"{conf*100:.1f}%")
        else:
            st.metric("Confidence", "N/A")

    with col4:
        if vol is not None:
            st.metric("Volatility", f"{vol*100:.2f}%")
        else:
            st.metric("Volatility", "N/A")

    if ts:
        st.caption(f"Timestamp: {ts}")

    show_confidence_chart(symbol, pred)


def show_history_table(history: list[dict]):
    if not history:
        st.info("No prediction history found.")
        return

    # Expect each item to have: symbol, predicted_price, prediction_time, horizon, confidence, volatility, trend
    rows = []
    for row in history:
        rows.append({
            "Symbol": row.get("symbol"),
            "Predicted Price": row.get("predicted_price"),
            "Prediction Time": row.get("prediction_time"),
            "Horizon": row.get("horizon"),
            "Confidence": row.get("confidence"),
            "Volatility": row.get("volatility"),
            "Trend": row.get("trend"),
        })

    st.dataframe(rows, use_container_width=True)


def show_assets_table(assets: list[dict]):
    if not assets:
        st.info("No assets found.")
        return

    rows = []
    for a in assets:
        rows.append({
            "Name": a.get("name"),
            "Symbol": a.get("symbol"),
            "Quantity": a.get("quantity"),
            "Avg Cost": a.get("avg_cost"),
        })

    st.dataframe(rows, use_container_width=True)


# -----------------------------
# UI
# -----------------------------
st.title("📊 Market Forecast Dashboard")



tickers = st.multiselect(
    "Select tickers",
    ["AAPL", "SPY", "QQQ", "MSFT", "TSLA"],
    default=["AAPL", "SPY"],
)

tab_forecasts, tab_history, tab_assets = st.tabs(["Forecasts", "Prediction History", "My Assets"])

# -----------------------------
# FORECASTS TAB
# -----------------------------
with tab_forecasts:
    st.subheader("Multi‑Ticker Forecasts")

    col_d, col_w, col_m = st.columns(3)

    with col_d:
        if st.button("Run DAILY predictions"):
            if not token:
                st.error("Please enter your token.")
            elif not tickers:
                st.error("Select at least one ticker.")
            else:
                data, err = call_api("/predict", {"tickers": tickers}, token)
                if err:
                    st.error(err)
                else:
                    # expect: { "AAPL": {...}, "SPY": {...}, ... }
                    for symbol, pred in data.items():
                        show_prediction_card(symbol, pred, "— Daily")

    with col_w:
        if st.button("Run WEEKLY forecasts"):
            if not token:
                st.error("Please enter your token.")
            elif not tickers:
                st.error("Select at least one ticker.")
            else:
                data, err = call_api("/predict/weekly", {"tickers": tickers}, token)
                if err:
                    st.error(err)
                else:
                    for symbol, pred in data.items():
                        show_prediction_card(symbol, pred, "— Weekly")

    with col_m:
        if st.button("Run MONTHLY forecasts"):
            if not token:
                st.error("Please enter your token.")
            elif not tickers:
                st.error("Select at least one ticker.")
            else:
                data, err = call_api("/predict/monthly", {"tickers": tickers}, token)
                if err:
                    st.error(err)
                else:
                    for symbol, pred in data.items():
                        show_prediction_card(symbol, pred, "— Monthly")

# -----------------------------
# HISTORY TAB
# -----------------------------
with tab_history:
    st.subheader("Prediction History")

    if st.button("Load prediction history"):
        if not token:
            st.error("Please enter your token.")
        else:
            # backend should expose something like: GET /predictions/history
            history, err = get_api("/predictions/history", token)
            if err:
                st.error(err)
            else:
                show_history_table(history)

# -----------------------------
# ASSETS TAB
# -----------------------------
with tab_assets:
    st.subheader("My Assets")

    if st.button("Load assets"):
        if not token:
            st.error("Please enter your token.")
        else:
            # you already have GET /assets in your backend
            assets, err = get_api("/assets", token)
            if err:
                st.error(err)
            else:
                show_assets_table(assets)

    st.markdown("### Quick forecast for my assets")
    if st.button("Run DAILY predictions for my assets"):
        if not token:
            st.error("Please enter your token.")
        else:
            assets, err = get_api("/assets", token)
            if err:
                st.error(err)
            else:
                symbols = [a.get("symbol") for a in assets if a.get("symbol")]
                if not symbols:
                    st.info("No symbols found in assets.")
                else:
                    data, err = call_api("/predict", {"tickers": symbols}, token)
                    if err:
                        st.error(err)
                    else:
                        for symbol, pred in data.items():
                            show_prediction_card(symbol, pred, "— Daily (My Assets)")
