import os
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf

# ---------------------------------------------------------
# App Initialization
# ---------------------------------------------------------
app = FastAPI()

# ---------------------------------------------------------
# CORS (allow frontend + Cloud Run)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-forecast")

# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class ForecastRequest(BaseModel):
    ticker: str
    days: int = 7

# ---------------------------------------------------------
# Health Check Endpoint (required for CI/CD)
# ---------------------------------------------------------
@app.get("/health")
def health():
    logger.info("HEALTH CHECK HIT")
    return {"status": "ok"}

# ---------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Market Forecast API is running"}

# ---------------------------------------------------------
# Forecast Endpoint
# ---------------------------------------------------------
@app.post("/forecast")
def forecast(req: ForecastRequest):
    try:
        ticker = req.ticker.upper()
        days = req.days

        logger.info(f"Fetching data for {ticker}")

        data = yf.download(ticker, period="1y", interval="1d")

        if data.empty:
            raise HTTPException(status_code=404, detail="Ticker not found or no data available")

        # Simple forecast logic (placeholder)
        last_price = float(data["Close"].iloc[-1])
        forecast_values = [round(last_price * (1 + 0.01 * i), 2) for i in range(1, days + 1)]

        return {
            "ticker": ticker,
            "last_price": last_price,
            "forecast_days": days,
            "forecast": forecast_values,
        }

    except Exception as e:
        logger.error(f"Error forecasting {req.ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# Generate Unique System User ID (example)
# ---------------------------------------------------------
@app.get("/system-user")
def system_user():
    return {"system_user_id": str(uuid.uuid4())}
@app.get("/health")
def health():
    return {"status": "ok"}

