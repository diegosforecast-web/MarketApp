import os
import yfinance as yf
from datetime import datetime, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_price_history(symbol: str, days: int = 90):
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    data = yf.download(
        symbol,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1d",
    )

    rows = []
    for idx, row in data.iterrows():
        rows.append({
            "symbol": symbol,
            "date": idx.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        })

    return rows


def save_price_history(user_id: str, symbol: str, rows: list):
    if not rows:
        return

    for r in rows:
        r["user_id"] = user_id

    supabase.table("price_history").insert(rows).execute()


def run_ingestion_for_user_asset(user_id: str, symbol: str):
    rows = fetch_price_history(symbol)
    save_price_history(user_id, symbol, rows)


if __name__ == "__main__":
    # simple manual test
    test_user_id = os.getenv("TEST_USER_ID")
    test_symbol = "AAPL"
    run_ingestion_for_user_asset(test_user_id, test_symbol)
