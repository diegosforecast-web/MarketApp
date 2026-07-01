"""
dependencies.py
===============
FastAPI dependency-injection helpers shared across routes.

Swap out ``get_data_loader`` with your real pipeline implementation.
``get_compare_config_overrides`` reads server-level defaults from env vars
so you can tune ranking weights or model paths without a code deploy.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loader dependency
# ---------------------------------------------------------------------------

def get_data_loader() -> Callable:
    """
    Returns the OHLCV data-loading callable used by CompareEngine.

    Resolution order:
    1. ``DATA_LOADER_BACKEND`` env var → ``"yfinance"`` | ``"alpaca"`` | ``"custom"``
    2. Falls back to yfinance if the var is unset or the backend fails to import.

    The returned callable has the signature:
        loader(symbol: str, start: str, end: str) -> pd.DataFrame
    """
    backend = os.getenv("DATA_LOADER_BACKEND", "yfinance").lower()

    if backend == "yfinance":
        return _yfinance_loader
    if backend == "alpaca":
        return _alpaca_loader
    if backend == "custom":
        # Expect the user to have wired up data.pipeline.load_ohlcv
        try:
            from data.pipeline import load_ohlcv  # type: ignore[import]
            return load_ohlcv
        except ImportError:
            logger.warning(
                "DATA_LOADER_BACKEND=custom but data.pipeline not importable. "
                "Falling back to yfinance."
            )
    return _yfinance_loader


def _yfinance_loader(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Download OHLCV via yfinance. Normalises column names to lowercase."""
    try:
        import yfinance as yf  # type: ignore[import]
    except ImportError:
        raise RuntimeError(
            "yfinance is not installed. Run: pip install yfinance"
        )

    df: pd.DataFrame = yf.download(
        symbol,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
    )

    if df.empty:
        raise ValueError(
            f"No data returned for symbol '{symbol}' in range {start}-{end}."
        )

    # Handle modern yfinance MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]).lower() for col in df.columns]
    else:
        df.columns = [str(col).lower() for col in df.columns]

    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)

    return df




def _alpaca_loader(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Download OHLCV via the Alpaca Markets Data API.

    Requires env vars: ALPACA_API_KEY, ALPACA_SECRET_KEY
    """
    try:
        from alpaca.data.historical import StockHistoricalDataClient  # type: ignore[import]
        from alpaca.data.requests import StockBarsRequest             # type: ignore[import]
        from alpaca.data.timeframe import TimeFrame                   # type: ignore[import]
    except ImportError:
        raise RuntimeError(
            "alpaca-trade-api is not installed. Run: pip install alpaca-py"
        )

    api_key = os.environ["ALPACA_API_KEY"]
    secret_key = os.environ["ALPACA_SECRET_KEY"]

    client = StockHistoricalDataClient(api_key, secret_key)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
    )
    bars = client.get_stock_bars(req).df
    bars = bars.reset_index(level=0, drop=True)
    bars.index = pd.to_datetime(bars.index)
    bars.rename(
        columns={"open": "open", "high": "high", "low": "low",
                 "close": "close", "volume": "volume"},
        inplace=True,
    )
    bars.sort_index(inplace=True)
    return bars


# ---------------------------------------------------------------------------
# Config overrides dependency
# ---------------------------------------------------------------------------

def get_compare_config_overrides() -> Dict[str, Any]:
    """
    Read server-level CompareConfig overrides from the environment.

    Supported env vars
    ------------------
    COMPARE_SEQUENCE_LENGTH        int
    COMPARE_INITIAL_CAPITAL        float
    COMPARE_TRANSACTION_COST_BPS   float
    COMPARE_RISK_FREE_RATE         float
    COMPARE_RANKING_WEIGHTS        JSON string, e.g. '{"sharpe_ratio":0.3,...}'
    LSTM_MODEL_PATH                str path
    GRU_MODEL_PATH                 str path
    ENSEMBLE_MODEL_PATH            str path
    GBM_MODEL_PATH                 str path
    """
    overrides: Dict[str, Any] = {}

    _maybe_int(overrides,   "sequence_length",       "COMPARE_SEQUENCE_LENGTH")
    _maybe_float(overrides, "initial_capital",       "COMPARE_INITIAL_CAPITAL")
    _maybe_float(overrides, "transaction_cost_bps",  "COMPARE_TRANSACTION_COST_BPS")
    _maybe_float(overrides, "risk_free_rate_annual", "COMPARE_RISK_FREE_RATE")
    _maybe_json(overrides,  "ranking_weights",       "COMPARE_RANKING_WEIGHTS")
    _maybe_str(overrides,   "lstm_model_path",       "LSTM_MODEL_PATH")
    _maybe_str(overrides,   "gru_model_path",        "GRU_MODEL_PATH")
    _maybe_str(overrides,   "ensemble_model_path",   "ENSEMBLE_MODEL_PATH")
    _maybe_str(overrides,   "gbm_model_path",        "GBM_MODEL_PATH")

    return overrides


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _maybe_int(target: dict, key: str, env_var: str) -> None:
    raw = os.getenv(env_var)
    if raw is not None:
        try:
            target[key] = int(raw)
        except ValueError:
            logger.warning("Env var %s='%s' is not a valid int; ignoring.", env_var, raw)


def _maybe_float(target: dict, key: str, env_var: str) -> None:
    raw = os.getenv(env_var)
    if raw is not None:
        try:
            target[key] = float(raw)
        except ValueError:
            logger.warning("Env var %s='%s' is not a valid float; ignoring.", env_var, raw)


def _maybe_str(target: dict, key: str, env_var: str) -> None:
    raw = os.getenv(env_var)
    if raw:
        target[key] = raw


def _maybe_json(target: dict, key: str, env_var: str) -> None:
    raw = os.getenv(env_var)
    if raw:
        try:
            target[key] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Env var %s is not valid JSON; ignoring. Value: %s", env_var, raw
            )
