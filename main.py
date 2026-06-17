import os
import datetime
import time
import numpy as np
import requests
from flask import Flask, request, jsonify
from supabase import create_client, Client
from tensorflow.keras.models import load_model
from tensorflow.keras.layers import LSTM

# -----------------------------
# SUPABASE INITIALIZATION
# -----------------------------
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("ERROR: Supabase env vars missing")
        return None

    try:
        client = create_client(url, key)
        print("Supabase initialized")
        return client
    except Exception as e:
        print("Supabase init error:", e)
        return None


supabase: Client = init_supabase()

DEFAULT_TICKERS = ["AAPL", "QQQ", "SPY"]

SYSTEM_USER_DAILY = "00000000-0000-0000-0000-000000000001"
SYSTEM_USER_WEEKLY = "00000000-0000-0000-0000-000000000002"
SYSTEM_USER_MONTHLY = "00000000-0000-0000-0000-000000000003"

app = Flask(__name__)

# -----------------------------
# MODEL LOADING (MULTI-MODEL)
# -----------------------------
MODEL_PATHS = {
    "AAPL": "models/aapl_lstm.h5",
    "QQQ":  "models/qqq_lstm.h5",
    "SPY":  "models/spy_lstm.h5",
}

loaded_models = {}  # cache


def get_model(symbol):
    if symbol not in MODEL_PATHS:
        raise ValueError(f"No model available for symbol {symbol}")

    if symbol in loaded_models:
        return loaded_models[symbol]

    print(f"[MODEL] Loading LSTM model for {symbol}...")

    def fixed_lstm(*args, **kwargs):
        kwargs.pop("time_major", None)
        return LSTM(*args, **kwargs)

    model = load_model(MODEL_PATHS[symbol], custom_objects={"LSTM": fixed_lstm})
    loaded_models[symbol] = model
    print(f"[MODEL] Model for {symbol} loaded")

    return model


# -----------------------------
# DATA FETCHING (ALPHA + YAHOO)
# -----------------------------
LOOKBACK = 60
price_cache = {}  # {symbol: (timestamp, prices)}


def fetch_alpha(symbol, lookback=LOOKBACK):
    api_key = os.getenv("ALPHA_KEY")
    if not api_key:
        raise ValueError("Missing ALPHA_KEY environment variable")

    url = (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
    )

    r = requests.get(url, timeout=10)
    data = r.json()

    if "Time Series (Daily)" not in data:
        raise ValueError(f"Alpha Vantage error: {data}")

    series = data["Time Series (Daily)"]
    closes = [float(v["4. close"]) for v in list(series.values())]

    if len(closes) < lookback:
        raise ValueError("Not enough Alpha data")

    closes = closes[::-1]  # oldest → newest
    return closes[-lookback:]


def fetch_yahoo(symbol, lookback=LOOKBACK):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()

    result = data["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    closes = [c for c in closes if c is not None]

    if len(closes) < lookback:
        raise ValueError("Not enough Yahoo data")

    return closes[-lookback:]


def fetch_with_retries(fetch_fn, symbol, retries=3, delay=2):
    for attempt in range(retries):
        try:
            prices = fetch_fn(symbol)
            print(f"[DATA] {symbol} fetched via {fetch_fn.__name__} on attempt {attempt+1}")
            return prices
        except Exception as e:
            print(f"[DATA] {symbol} {fetch_fn.__name__} attempt {attempt+1} failed:", e)
            time.sleep(delay)
    raise Exception(f"All retries failed for {symbol} via {fetch_fn.__name__}")


def fetch_recent_prices(symbol, lookback=LOOKBACK):
    now = datetime.datetime.utcnow()

    # Cache: 60 seconds
    if symbol in price_cache:
        ts, data = price_cache[symbol]
        if (now - ts).seconds < 60:
            print(f"[CACHE] Using cached prices for {symbol}")
            return data

    # Try Alpha first
    try:
        prices = fetch_with_retries(lambda s: fetch_alpha(s, lookback), symbol)
    except Exception as e_alpha:
        print(f"[DATA] Alpha failed for {symbol}, falling back to Yahoo:", e_alpha)
        prices = fetch_with_retries(lambda s: fetch_yahoo(s, lookback), symbol)

    price_cache[symbol] = (now, prices)
    return prices


def prepare_input(series):
    arr = np.array(series).reshape(1, LOOKBACK, 1)
    return arr


# -----------------------------
# LSTM PREDICTION
# -----------------------------
def predict_price(symbol: str, horizon_days: int = 1):
    mdl = get_model(symbol)

    prices = fetch_recent_prices(symbol)
    x = prepare_input(prices)

    y_pred = mdl.predict(x)
    prediction_value = float(y_pred[0][0])

    prediction_time = datetime.datetime.utcnow().isoformat() + "Z"

    print(f"[PREDICT] {symbol} → {prediction_value} at {prediction_time}")
    return prediction_value, prediction_time


# -----------------------------
# SUPABASE UPSERT
# -----------------------------
def save_prediction_to_supabase(user_id, symbol, prediction_value, prediction_time, horizon: str):
    if supabase is None:
        print("[SUPABASE] Not initialized")
        return {"error": "Supabase not initialized"}

    prediction_date = prediction_time[:10]

    data = {
        "user_id": user_id,
        "symbol": symbol,
        "predicted_price": prediction_value,
        "prediction_value": float(prediction_value),
        "prediction_time": prediction_time,
        "prediction_date": prediction_date,
        "horizon": horizon,
        "asset_id": None
    }

    try:
        response = supabase.table("predictions").insert(data, upsert=True).execute()
        print(f"[SUPABASE] UPSERT {symbol} {horizon} →", response)
        return response
    except Exception as e:
        print(f"[SUPABASE] UPSERT ERROR for {symbol} {horizon}:", e)
        return {"error": str(e)}


# -----------------------------
# MANUAL PREDICT ENDPOINT
# -----------------------------
@app.route("/predict", methods=["POST"])
def predict():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    body = request.get_json() or {}
    symbol = body.get("symbol")

    if not symbol:
        return jsonify({"status": "error", "message": "symbol required"}), 400

    try:
        prediction_value, prediction_time = predict_price(symbol)

        save_prediction_to_supabase(
            user_id=user_id,
            symbol=symbol,
            prediction_value=prediction_value,
            prediction_time=prediction_time,
            horizon="manual_daily",
        )

        return jsonify({
            "status": "ok",
            "data": {
                "symbol": symbol,
                "prediction": prediction_value,
                "timestamp": prediction_time,
            }
        })

    except Exception as e:
        print("[ERROR] /predict:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------
# AUTO JOB ENDPOINTS
# -----------------------------
@app.route("/predict/daily_auto", methods=["POST"])
def predict_daily_auto():
    return run_auto_predictions(SYSTEM_USER_DAILY, "daily", 1)


@app.route("/predict/weekly_auto", methods=["POST"])
def predict_weekly_auto():
    return run_auto_predictions(SYSTEM_USER_WEEKLY, "weekly", 7)


@app.route("/predict/monthly_auto", methods=["POST"])
def predict_monthly_auto():
    return run_auto_predictions(SYSTEM_USER_MONTHLY, "monthly", 30)


def run_auto_predictions(system_user_id, horizon, horizon_days):
    results = {}

    try:
        for symbol in DEFAULT_TICKERS:
            prediction_value, prediction_time = predict_price(symbol, horizon_days)

            save_prediction_to_supabase(
                user_id=system_user_id,
                symbol=symbol,
                prediction_value=prediction_value,
                prediction_time=prediction_time,
                horizon=horizon,
            )

            results[symbol] = {
                "prediction": prediction_value,
                "timestamp": prediction_time,
                "horizon": horizon,
            }

        print(f"[JOB] {horizon} auto completed:", results)
        return jsonify({"status": "ok", "data": results})

    except Exception as e:
        print(f"[ERROR] /predict/{horizon}_auto:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
