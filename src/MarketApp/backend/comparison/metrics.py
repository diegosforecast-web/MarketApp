"""
metrics.py
==========
Standardized metrics computation for every model result.

Computed metrics
----------------
| Key                  | Description                                          |
|----------------------|------------------------------------------------------|
| mae                  | Mean Absolute Error (price units)                    |
| rmse                 | Root Mean Squared Error (price units)                |
| mape                 | Mean Absolute Percentage Error (%)                   |
| directional_accuracy | % of correctly predicted price direction moves       |
| backtest_return      | Cumulative return of the model's long/short strategy |
| sharpe_ratio         | Annualised Sharpe ratio (252 trading days)           |
| max_drawdown         | Maximum peak-to-trough drawdown (fraction)           |
| ci_width             | Mean width of prediction interval (price units)      |
| latency_ms           | Inference wall-clock time in milliseconds            |
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .compare_engine import CompareConfig, ModelResult

logger = logging.getLogger(__name__)

_TRADING_DAYS = 252
_EPS = 1e-9  # guard against division by zero


class MetricsEngine:
    """Compute all comparison metrics from a ModelResult."""

    def __init__(self, config: "CompareConfig") -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def compute(self, result: "ModelResult") -> Dict[str, float]:
        """
        Return a flat dict of metric_name → float for a single ModelResult.
        All metrics are normalised so that *higher is always better* from the
        ranker's perspective (see _normalise_direction).
        """
        preds = result.predictions
        actuals = result.actuals

        if len(preds) == 0 or len(actuals) == 0:
            raise ValueError(f"Empty arrays for model {result.model_name}")

        metrics: Dict[str, float] = {}

        # --- Prediction error metrics ------------------------------------
        metrics["mae"] = self._mae(preds, actuals)
        metrics["rmse"] = self._rmse(preds, actuals)
        metrics["mape"] = self._mape(preds, actuals)
        metrics["directional_accuracy"] = self._directional_accuracy(preds, actuals)

        # --- Strategy / backtest metrics ---------------------------------
        returns = self._strategy_returns(preds, actuals)
        metrics["backtest_return"] = float(np.prod(1.0 + returns) - 1.0)
        metrics["sharpe_ratio"] = self._sharpe(returns)
        metrics["max_drawdown"] = self._max_drawdown(returns)

        # --- Uncertainty metric ------------------------------------------
        metrics["ci_width"] = self._ci_width(result.prediction_intervals)

        # --- Latency -------------------------------------------------------
        metrics["latency_ms"] = result.latency_ms

        return {k: round(float(v), 6) for k, v in metrics.items()}

    # ------------------------------------------------------------------
    # Individual metric implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _mae(preds: np.ndarray, actuals: np.ndarray) -> float:
        return float(np.mean(np.abs(preds - actuals)))

    @staticmethod
    def _rmse(preds: np.ndarray, actuals: np.ndarray) -> float:
        return float(np.sqrt(np.mean((preds - actuals) ** 2)))

    @staticmethod
    def _mape(preds: np.ndarray, actuals: np.ndarray) -> float:
        denominator = np.where(np.abs(actuals) < _EPS, _EPS, np.abs(actuals))
        return float(np.mean(np.abs((preds - actuals) / denominator)) * 100.0)

    @staticmethod
    def _directional_accuracy(preds: np.ndarray, actuals: np.ndarray) -> float:
        if len(preds) < 2:
            return 0.0
        actual_dir = np.sign(np.diff(actuals))
        pred_dir = np.sign(np.diff(preds))
        correct = np.sum(actual_dir == pred_dir)
        return float(correct / len(actual_dir) * 100.0)

    @staticmethod
    def _strategy_returns(preds: np.ndarray, actuals: np.ndarray) -> np.ndarray:
        """
        Simple long/short strategy:
        - Go long (+1) when predicted price rises vs. previous actual.
        - Go short (-1) when predicted price falls.
        - Multiply by actual next-period return.
        """
        if len(preds) < 2:
            return np.array([0.0])
        signals = np.sign(np.diff(preds))          # +1 / -1 / 0
        actual_returns = np.diff(actuals) / (np.abs(actuals[:-1]) + _EPS)
        return signals * actual_returns

    def _sharpe(self, returns: np.ndarray) -> float:
        if len(returns) < 2:
            return 0.0
        rfr_daily = (1.0 + self.config.risk_free_rate_annual) ** (1.0 / _TRADING_DAYS) - 1.0
        excess = returns - rfr_daily
        std = np.std(excess, ddof=1)
        if std < _EPS:
            return 0.0
        return float(np.mean(excess) / std * np.sqrt(_TRADING_DAYS))

    @staticmethod
    def _max_drawdown(returns: np.ndarray) -> float:
        if len(returns) == 0:
            return 0.0
        cumulative = np.cumprod(1.0 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + _EPS)
        return float(np.min(drawdown))  # most negative value

    def _ci_width(self, intervals: Optional[np.ndarray]) -> float:
        """Mean width of prediction interval. 0.0 if not provided."""
        if intervals is None or len(intervals) == 0:
            return 0.0
        widths = intervals[:, 1] - intervals[:, 0]
        return float(np.mean(np.abs(widths)))


# ---------------------------------------------------------------------------
# Standalone helper used by the serializer to build per-step chart data
# ---------------------------------------------------------------------------

def rolling_directional_accuracy(
    preds: np.ndarray,
    actuals: np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Return rolling directional-accuracy array (length == len(preds) - 1)."""
    if len(preds) < 2:
        return np.array([])
    actual_dir = np.sign(np.diff(actuals))
    pred_dir = np.sign(np.diff(preds))
    correct = (actual_dir == pred_dir).astype(float)
    kernel = np.ones(window) / window
    return np.convolve(correct, kernel, mode="valid") * 100.0
