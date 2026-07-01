import pandas as pd
import os

# Path to your existing CSV
csv_path = r"C:\Dev\MarketApp\src\MarketApp\backend\data\price_history.csv"

# Load the Close-only CSV
df = pd.read_csv(csv_path)

# Normalize column names
df = df.rename(columns={"Date": "date", "Close": "close"})

# Generate minimal OHLCV from Close-only data
df["open"] = df["close"]
df["high"] = df["close"]
df["low"] = df["close"]
df["volume"] = 0

# Reorder columns to match your pipeline
df = df[["date", "open", "high", "low", "close", "volume"]]

# Save back to the same file
df.to_csv(csv_path, index=False)

print("Converted price_history.csv to OHLCV format successfully.")
