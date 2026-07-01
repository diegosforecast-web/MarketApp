import yfinance as yf
import pandas as pd

ticker = "AAPL"
df = yf.download(ticker, period="6mo")  # 6 months of data

df = df.reset_index()
df = df.rename(columns={
    "Date": "date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume"
})

df = df[["date", "open", "high", "low", "close", "volume"]]

df.to_csv(r"C:\Dev\MarketApp\src\MarketApp\backend\data\price_history.csv", index=False)

print("Downloaded and saved AAPL OHLCV data.")
