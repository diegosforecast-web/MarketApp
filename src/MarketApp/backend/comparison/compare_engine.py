"""
compare_engine.py
=================
Core orchestration layer for the Model Comparison module.

Responsibilities
----------------
- Load OHLCV data from the data pipeline.
- Dispatch predictions to every model runner (LSTM, GRU, Ensemble, GBM).
- Collect raw predictions + latency per model.
- Hand off to MetricsEngine → ModelRanker → ComparisonSerializer.
- Return a single frontend-ready dict.

Usage
-----
    engine = CompareEngine(config)
    result = await engine.run(symbol="AAPL", start="2024-01-01", end="2024-12-31")
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .metrics import MetricsEngine
from .model_runners.gbm_runner import GBMRunner
from .model_runners.gru_runner import GRURunner
from .model_runners.lstm_runner import LSTMRunner
from .model_runners.ensemble_runner import EnsembleRunner
from .ranking import ModelRanker
from .serializer import ComparisonSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class CompareConfig:
    """All tuneable knobs for a comparison run."""

    # Data
    price_column: str = "close"
    feature_columns: List[str] = field(
        default_factory=lambda: ["open", "high", "low", "close", "volume"]
    )
    sequence_length: int = 60          # lookback window for RNN models

    # Backtest
    initial_capital: float = 100_000.0
    transaction_cost_bps: float = 5.0  # basis points per trade

    # Metrics
    risk_free_rate_annual: float = 0.05
    confidence_level: float = 0.95     # for CI width

    # Ranking weights (must sum to 1.0)
    ranking_weights: Dict[str, float] = field(default_factory=lambda: {
        "mae":                  0.10,
        "rmse":                 0.10,
        "mape":                 0.10,
        "directional_accuracy": 0.15,
        "backtest_return":      0.20,
        "sharpe_ratio":         0.20,
        "max_drawdown":         0.10,
        "ci_width":             0.05,
    })

    # Runner-level overrides (passed straight to each model loader)
    lstm_model_path: Optional[str] = None
    gru_model_path: Optional[str] = None
    ensemble_model_path: Optional[str] = None
    gbm_model_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Per-model raw result container
# ---------------------------------------------------------------------------

@dataclass
class ModelResult:
    model_name: str
    predictions: np.ndarray        # shape (n,)
    actuals: np.ndarray            # shape (n,)
    dates: pd.DatetimeIndex
    prediction_intervals: Optional[np.ndarray] = None  # shape (n, 2) – [lo, hi]
    latency_ms: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class CompareEngine:
    """
    Orchestrates a full model-comparison run.

    Parameters
    ----------
    config : CompareConfig
        Runtime configuration. Defaults to CompareConfig() if omitted.
    data_loader : callable, optional
        ``data_loader(symbol, start, end) -> pd.DataFrame`` that returns
        a DataFrame with at minimum OHLCV columns indexed by date.
        Defaults to the built-in ``_default_data_loader``.
    """

    MODEL_NAMES = ("LSTM", "GRU", "Ensemble", "GBM")

    def __init__(
        self,
        config: Optional[CompareConfig] = None,
        data_loader: Optional[Any] = None,
    ) -> None:
        self.config = config or CompareConfig()
        self._data_loader = data_loader or _default_data_loader

        # Instantiate runners (they are lazy – models load on first predict)
        self._runners = {
            "LSTM":     LSTMRunner(model_path=self.config.lstm_model_path),
            "GRU":      GRURunner(model_path=self.config.gru_model_path),
            "Ensemble": EnsembleRunner(model_path=self.config.ensemble_model_path),
            "GBM":      GBMRunner(model_path=self.config.gbm_model_path),
        }

        self._metrics_engine = MetricsEngine(self.config)
        self._ranker = ModelRanker(self.config.ranking_weights)
        self._serializer = ComparisonSerializer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        symbol: str,
        start: str,
        end: str,
        models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full comparison pipeline.

        Parameters
        ----------
        symbol : str
            Ticker symbol, e.g. ``"AAPL"``.
        start : str
            ISO-8601 start date, e.g. ``"2024-01-01"``.
        end : str
            ISO-8601 end date, e.g. ``"2024-12-31"``.
        models : list[str], optional
            Subset of models to run. Defaults to all four.

        Returns
        -------
        dict
            Frontend-ready comparison payload.
        """
        active_models = models or list(self.MODEL_NAMES)
        logger.info(
            "CompareEngine.run | symbol=%s  start=%s  end=%s  models=%s",
            symbol, start, end, active_models,
        )

        # 1. Load data -------------------------------------------------------
        ohlcv: pd.DataFrame = await asyncio.get_event_loop().run_in_executor(
            None, self._data_loader, symbol, start, end
        )
        _validate_ohlcv(ohlcv, self.config.feature_columns)

        # 2. Dispatch model predictions in parallel --------------------------
        tasks = [
            self._run_single_model(name, ohlcv)
            for name in active_models
            if name in self._runners
        ]
        raw_results: List[ModelResult] = await asyncio.gather(*tasks)

        # 3. Compute metrics -------------------------------------------------
        metrics_map: Dict[str, Dict[str, float]] = {}
        for result in raw_results:
            if result.error:
                logger.warning("Model %s failed: %s", result.model_name, result.error)
                continue
            metrics_map[result.model_name] = self._metrics_engine.compute(result)

        if not metrics_map:
            raise RuntimeError("All models failed. Cannot produce comparison.")

        # 4. Rank models -----------------------------------------------------
        ranking = self._ranker.rank(metrics_map)

        # 5. Serialize -------------------------------------------------------
        return self._serializer.build(
            symbol=symbol,
            start=start,
            end=end,
            raw_results=raw_results,
            metrics_map=metrics_map,
            ranking=ranking,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_single_model(
        self, name: str, ohlcv: pd.DataFrame
    ) -> ModelResult:
        runner = self._runners[name]
        t0 = time.perf_counter()
        try:
            preds, actuals, dates, intervals = await asyncio.get_event_loop().run_in_executor(
                None,
                runner.predict,
                ohlcv,
                self.config.sequence_length,
                self.config.price_column,
            )
            latency_ms = (time.perf_counter() - t0) * 1_000
            return ModelResult(
                model_name=name,
                predictions=np.asarray(preds),
                actuals=np.asarray(actuals),
                dates=dates,
                prediction_intervals=intervals,
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Runner %s raised an exception", name)
            return ModelResult(
                model_name=name,
                predictions=np.array([]),
                actuals=np.array([]),
                dates=pd.DatetimeIndex([]),
                error=str(exc),
                latency_ms=(time.perf_counter() - t0) * 1_000,
            )


# ---------------------------------------------------------------------------
# Default data loader (replace with your real pipeline adapter)
# ---------------------------------------------------------------------------

def _default_data_loader(
    symbol: str, start: str, end: str
) -> pd.DataFrame:
    """
    Stub data loader.  Replace or monkey-patch with your actual data pipeline.

    Expected return shape:
        pd.DataFrame with DatetimeIndex and columns:
        ['open', 'high', 'low', 'close', 'volume']
    """
    raise NotImplementedError(
        "Supply a data_loader callable to CompareEngine or replace "
        "_default_data_loader with your pipeline adapter."
    )


def _validate_ohlcv(df: pd.DataFrame, required_cols: List[str]) -> None:
    if df is None or df.empty:
        raise ValueError("Data loader returned empty DataFrame.")
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV DataFrame missing columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("OHLCV DataFrame must have a DatetimeIndex.")
