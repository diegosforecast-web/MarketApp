from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf


class MarketDataService:
    ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

    def __init__(
        self,
        cache_dir: str | Path = "data/market_cache",
        minimum_rows: int = 260,
    ) -> None:
        self.alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.cache_dir = Path(cache_dir)
        self.minimum_rows = minimum_rows
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, ticker: str) -> Path:
        safe = ticker.upper().replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.cache_dir / f"{safe}.csv"

    @staticmethod
    def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            raise RuntimeError("Market-data provider returned no rows.")

        out = df.copy()

        if isinstance(out.columns, pd.MultiIndex):
            out.columns = [
                str(column[0]).lower()
                for column in out.columns.to_flat_index()
            ]
        else:
            out.columns = [str(column).lower() for column in out.columns]

        if "date" not in out.columns:
            out = out.reset_index()
            out = out.rename(columns={out.columns[0]: "date"})

        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [column for column in required if column not in out.columns]

        if missing:
            raise RuntimeError(
                f"Market data is missing required columns: {missing}"
            )

        out = out[required].copy()
        out["date"] = pd.to_datetime(
            out["date"],
            errors="coerce",
            utc=True,
        ).dt.tz_localize(None)

        numeric = ["open", "high", "low", "close", "volume"]
        out[numeric] = out[numeric].apply(pd.to_numeric, errors="coerce")

        out = (
            out.dropna(subset=required)
            .sort_values("date")
            .drop_duplicates(subset=["date"], keep="last")
            .reset_index(drop=True)
        )

        if out.empty:
            raise RuntimeError("Market data contains no usable rows.")

        return out

    def _validate_history(self, ticker: str, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < self.minimum_rows:
            raise RuntimeError(
                f"Only {len(df)} daily rows are available for {ticker}; "
                f"DiMarket requires at least {self.minimum_rows} rows."
            )
        return df

    def _load_cache(self, ticker: str) -> pd.DataFrame | None:
        path = self._cache_path(ticker)
        if not path.exists():
            return None
        return self._normalize_frame(pd.read_csv(path))

    def _save_cache(self, ticker: str, df: pd.DataFrame) -> None:
        df.to_csv(self._cache_path(ticker), index=False)

    @staticmethod
    def _merge_history(
        older: pd.DataFrame | None,
        newer: pd.DataFrame,
    ) -> pd.DataFrame:
        if older is None or older.empty:
            return newer

        return (
            pd.concat([older, newer], ignore_index=True)
            .sort_values("date")
            .drop_duplicates(subset=["date"], keep="last")
            .reset_index(drop=True)
        )

    def _download_yfinance(self, ticker: str) -> pd.DataFrame:
        raw = yf.download(
            ticker,
            period="10y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=30,
        )
        return self._normalize_frame(raw)

    def _download_alpha_vantage_compact(self, ticker: str) -> pd.DataFrame:
        if not self.alpha_vantage_api_key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is not configured.")

        response = requests.get(
            self.ALPHA_VANTAGE_URL,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "compact",
                "apikey": self.alpha_vantage_api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        series = payload.get("Time Series (Daily)")
        if not series:
            message = (
                payload.get("Note")
                or payload.get("Information")
                or payload.get("Error Message")
                or "Unexpected Alpha Vantage response."
            )
            raise RuntimeError(message)

        frame = (
            pd.DataFrame.from_dict(series, orient="index")
            .rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                    "5. volume": "volume",
                }
            )
            .reset_index()
            .rename(columns={"index": "date"})
        )
        return self._normalize_frame(frame)

    def get_intraday_history(
        self,
        ticker: str,
        *,
        period: str = "60d",
        interval: str = "5m",
    ) -> pd.DataFrame:
        """
        Download recent historical intraday bars.

        This allows DiMarket to determine whether a saved predicted
        price was reached without continuously streaming live quotes.
        """
        ticker = ticker.strip().upper()

        if not ticker:
            raise ValueError("Ticker is required.")

        raw = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
            prepost=False,
            timeout=30,
        )

        if raw is None or raw.empty:
            raise RuntimeError(
                f"No intraday market data returned for {ticker}."
            )

        frame = raw.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [
                str(column[0]).lower()
                for column in frame.columns.to_flat_index()
            ]
        else:
            frame.columns = [
                str(column).lower()
                for column in frame.columns
            ]

        frame = frame.reset_index()
        frame = frame.rename(
            columns={
                frame.columns[0]: "timestamp",
            }
        )

        required = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        missing = [
            column
            for column in required
            if column not in frame.columns
        ]

        if missing:
            raise RuntimeError(
                "Intraday market data is missing required "
                f"columns: {missing}"
            )

        frame = frame[required].copy()

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            errors="coerce",
            utc=True,
        )

        numeric = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        frame[numeric] = frame[numeric].apply(
            pd.to_numeric,
            errors="coerce",
        )

        frame = (
            frame.dropna(subset=required)
            .sort_values("timestamp")
            .drop_duplicates(
                subset=["timestamp"],
                keep="last",
            )
            .reset_index(drop=True)
        )

        if frame.empty:
            raise RuntimeError(
                "Intraday market data contains no usable rows."
            )

        return frame
    def get_history(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.strip().upper()
        if not ticker:
            raise ValueError("Ticker is required.")

        cached = self._load_cache(ticker)
        errors: list[str] = []

        try:
            yahoo = self._download_yfinance(ticker)
            merged = self._merge_history(cached, yahoo)
            merged = self._validate_history(ticker, merged)
            self._save_cache(ticker, merged)
            return merged
        except Exception as exc:
            errors.append(f"Yahoo Finance: {exc}")

        try:
            alpha = self._download_alpha_vantage_compact(ticker)
            merged = self._merge_history(cached, alpha)
            merged = self._validate_history(ticker, merged)
            self._save_cache(ticker, merged)
            return merged
        except Exception as exc:
            errors.append(f"Alpha Vantage: {exc}")

        if cached is not None:
            return self._validate_history(ticker, cached)

        raise RuntimeError(
            f"Unable to retrieve sufficient market data for {ticker}. "
            f"No ticker-specific cache is available. {' | '.join(errors)}"
        )

