import requests
import os
import pandas as pd


ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


def load_price_history(ticker: str):
    if not ALPHA_VANTAGE_API_KEY:
        raise Exception("Missing ALPHA_VANTAGE_API_KEY environment variable.")

    url = (
        "https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}&outputsize=compact"
    )

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Alpha Vantage request failed: {response.status_code}")

    data = response.json()

    if "Time Series (Daily)" not in data:
        raise Exception(f"Unexpected Alpha Vantage response: {data}")

    ts = data["Time Series (Daily)"]

    df = pd.DataFrame.from_dict(ts, orient="index")
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)

    closes = df["4. close"].astype(float).tolist()

    return closes
