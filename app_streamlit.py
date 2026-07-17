import os

import requests
import streamlit as st

from ui.charts import render_driver_charts
from ui.explanation import render_explanation
from ui.forecast_form import render_forecast_form
from ui.header import render_header
from ui.history import render_historical_confidence
from ui.metrics import render_forecast_metrics
from ui.sidebar import render_sidebar
from ui.theme import apply_theme


BACKEND_URL = os.getenv(
    "DIMARKET_BACKEND_URL",
    "http://127.0.0.1:8000",
)


st.set_page_config(
    page_title="DiMarket",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)


def call_forecast(
    ticker: str,
    horizon: int,
) -> dict:
    response = requests.get(
        f"{BACKEND_URL}/forecast/",
        params={
            "ticker": ticker,
            "horizon": horizon,
        },
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


apply_theme()
render_sidebar()
render_header()

ticker, horizon, submitted = render_forecast_form()

if submitted:
    clean_ticker = ticker.upper().strip()

    if not clean_ticker:
        st.error("Please enter a ticker.")
        st.stop()

    try:
        with st.spinner("Running DiMarket AI forecast..."):
            data = call_forecast(
                ticker=clean_ticker,
                horizon=horizon,
            )

        render_forecast_metrics(data)

        explanation = data.get("explanation")
        if explanation:
            render_explanation(explanation)
            render_driver_charts(explanation)

        historical = data.get("historical_confidence")
        if historical:
            render_historical_confidence(historical)

    except Exception as exc:
        st.error(f"Forecast failed: {exc}")
