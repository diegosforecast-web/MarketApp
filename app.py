from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import datetime
import tensorflow as tf
import pickle
import os
import yfinance as yf

app = FastAPI()

# ---------------------------------------------------
# Root Route (Fixes Cloud Run "Not Found")
# ---------------------------------------------------
@app.get("/")
def root():
    return {"status": "running", "message": "FastAPI is live"}

# ---------------------------------------------------
# Health Check
# ---------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------------------------------------------
# Request model
# ---------------------------------------------------
class ForecastRequest(BaseModel):
    ticker: str
    days: int = 1

# ---------------------------------------------------
# Paths for model + scaler
# ---------------------------------------------------
MODEL_PATH = "models/lstm_model.h5"
SCALER_PATH = "models/scaler.pkl"

model = None
scaler = None

def load_assets():
    """Load model and scaler once per container."""
    global model, scaler

    if model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        model = tf.keras.models.load_model(MODEL_PATH)

    if scaler is None:
        if not os.path.exists(SCALER_PATH):
            raise FileNotFoundError(f"Scaler not found at {SCALER_PATH}")
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)

# ---------------------------------------------------
# Fetch last 60 closes from Yahoo Finance
# ---------------------------------------------------
def fetch_last_60_closes(ticker: str):
    data = yf.download(ticker, period="90d", interval="1d")
    closes = data["Close"].dropna().values

    if len(closes) < 60:
        raise ValueError(f"Not enough data for {ticker}. Needed 60 closes, got {len(closes)}.")

    return closes[-60:]

# ---------------------------------------------------
# Preprocessing helper
# ---------------------------------------------------
def prepare_input(last_sequence):
    seq = last_sequence.reshape(-1, 1)
    seq_scaled = scaler.transform(seq)
    return seq_scaled.reshape(1, 60, 1)

# ---------------------------------------------------
# Real model inference with real data
# ---------------------------------------------------
def run_model(ticker: str, days: int):
    load_assets()

    last_60 = fetch_last_60_closes(ticker)
    X = prepare_input(last_60)

    pred_scaled = model.predict(X)[0][0]
    pred = scaler.inverse_transform([[pred_scaled]])[0][0]

    return float(pred)

# ---------------------------------------------------
# Forecast Endpoint
# ---------------------------------------------------
@app.post("/forecast")
def forecast(req: ForecastRequest):
    try:
        pred = run_model(req.ticker, req.days)

        return {
            "ticker": req.ticker.upper(),
            "days_ahead": req.days,
            "prediction": pred,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
