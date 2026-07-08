import os
import requests
import pandas as pd


class MarketDataService:
    """
    Retrieves historical market data for forecasting models.
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "ALPHA_VANTAGE_API_KEY environment variable is not set."
            )

    def get_history(self, ticker: str) -> pd.DataFrame:
        """
        Returns the full available daily OHLCV history for a ticker.
        """

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker.upper(),
            "outputsize": "compact",      # <-- Changed from compact
            "apikey": self.api_key,
        }

        response = requests.get(
            self.BASE_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()

        if "Time Series (Daily)" not in payload:
            raise RuntimeError(
                f"Unexpected Alpha Vantage response: {payload}"
            )

        df = (
            pd.DataFrame.from_dict(
                payload["Time Series (Daily)"],
                orient="index",
            )
            .rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                    "5. volume": "volume",
                }
            )
        )

        # Convert index to datetime
        df.index = pd.to_datetime(df.index)

        # Make the index a normal column
        df = df.reset_index().rename(columns={"index": "date"})

        # Convert numeric columns
        numeric_cols = ["open", "high", "low", "close", "volume"]
        df[numeric_cols] = df[numeric_cols].astype(float)

        # Sort oldest → newest
        df = df.sort_values("date").reset_index(drop=True)

        return df