"""
test_metrics.py
===============
Unit tests for MetricsEngine.

Run with:  pytest comparison/tests/test_metrics.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from comparison.compare_engine import CompareConfig, ModelResult
from comparison.metrics import MetricsEngine

import pandas as pd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def config() -> CompareConfig:
    return CompareConfig()


@pytest.fixture()
def engine(config) -> MetricsEngine:
    return MetricsEngine(config)


def _make_result(
    preds: np.ndarray,
    actuals: np.ndarray,
    name: str = "TEST",
    intervals: np.ndarray | None = None,
    latency_ms: float = 10.0,
) -> ModelResult:
    dates = pd.date_range("2024-01-01", periods=len(preds), freq="B")
    return ModelResult(
        model_name=name,
        predictions=preds,
        actuals=actuals,
        dates=dates,
        prediction_intervals=intervals,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# MAE
# ---------------------------------------------------------------------------

class TestMAE:
    def test_perfect_predictions(self, engine):
        arr = np.array([100.0, 110.0, 120.0])
        result = _make_result(arr, arr)
        assert engine.compute(result)["mae"] == pytest.approx(0.0, abs=1e-6)

    def test_constant_offset(self, engine):
        actuals = np.array([100.0, 200.0, 300.0])
        preds   = actuals + 10.0
        result = _make_result(preds, actuals)
        assert engine.compute(result)["mae"] == pytest.approx(10.0, rel=1e-4)

    def test_mixed_signs(self, engine):
        actuals = np.array([100.0, 100.0])
        preds   = np.array([90.0, 110.0])
        result = _make_result(preds, actuals)
        assert engine.compute(result)["mae"] == pytest.approx(10.0, rel=1e-4)


# ---------------------------------------------------------------------------
# RMSE
# ---------------------------------------------------------------------------

class TestRMSE:
    def test_rmse_greater_than_mae_for_variable_errors(self, engine):
        actuals = np.array([100.0, 100.0, 100.0])
        preds   = np.array([90.0, 100.0, 120.0])   # errors: -10, 0, +20
        m = engine.compute(_make_result(preds, actuals))
        assert m["rmse"] >= m["mae"]

    def test_rmse_equals_mae_for_uniform_errors(self, engine):
        actuals = np.array([100.0, 200.0, 300.0])
        preds   = actuals + 5.0
        m = engine.compute(_make_result(preds, actuals))
        assert m["rmse"] == pytest.approx(m["mae"], rel=1e-4)


# ---------------------------------------------------------------------------
# MAPE
# ---------------------------------------------------------------------------

class TestMAPE:
    def test_mape_five_percent(self, engine):
        actuals = np.array([100.0, 200.0])
        preds   = np.array([105.0, 210.0])
        m = engine.compute(_make_result(preds, actuals))
        assert m["mape"] == pytest.approx(5.0, rel=1e-3)

    def test_mape_near_zero_actuals(self, engine):
        """Should not raise ZeroDivisionError."""
        actuals = np.array([1e-10, 100.0])
        preds   = np.array([0.0,   100.0])
        m = engine.compute(_make_result(preds, actuals))
        assert np.isfinite(m["mape"])


# ---------------------------------------------------------------------------
# Directional Accuracy
# ---------------------------------------------------------------------------

class TestDirectionalAccuracy:
    def test_perfect_direction(self, engine):
        actuals = np.array([100.0, 110.0, 120.0, 130.0])
        preds   = np.array([100.0, 105.0, 115.0, 125.0])
        m = engine.compute(_make_result(preds, actuals))
        assert m["directional_accuracy"] == pytest.approx(100.0)

    def test_worst_direction(self, engine):
        actuals = np.array([100.0, 110.0, 120.0])   # always up
        preds   = np.array([100.0,  90.0,  80.0])   # always predicts down
        m = engine.compute(_make_result(preds, actuals))
        assert m["directional_accuracy"] == pytest.approx(0.0)

    def test_50_percent(self, engine):
        actuals = np.array([100.0, 110.0, 105.0, 115.0])  # up, down, up
        preds   = np.array([100.0, 105.0, 110.0, 120.0])  # up, up,   up  → 2/3 correct
        m = engine.compute(_make_result(preds, actuals))
        # 2 out of 3 directions correct
        assert m["directional_accuracy"] == pytest.approx(2 / 3 * 100, rel=1e-3)


# ---------------------------------------------------------------------------
# Sharpe ratio
# ---------------------------------------------------------------------------

class TestSharpe:
    def test_positive_sharpe_for_trending_predictions(self, engine):
        n = 200
        actuals = np.linspace(100, 200, n)
        # Predictions slightly lag actuals but follow the trend
        preds   = np.concatenate([[100.0], actuals[:-1]])
        m = engine.compute(_make_result(preds, actuals))
        assert m["sharpe_ratio"] > 0

    def test_zero_sharpe_for_flat_returns(self, engine):
        actuals = np.full(50, 100.0)
        preds   = np.full(50, 100.0)
        m = engine.compute(_make_result(preds, actuals))
        assert m["sharpe_ratio"] == pytest.approx(0.0, abs=1e-5)


# ---------------------------------------------------------------------------
# Max drawdown
# ---------------------------------------------------------------------------

class TestMaxDrawdown:
    def test_no_drawdown_for_perfect_uptrend(self, engine):
        n = 100
        actuals = np.linspace(100, 200, n)
        preds   = np.concatenate([[100.0], actuals[:-1]])
        m = engine.compute(_make_result(preds, actuals))
        assert m["max_drawdown"] >= -0.1   # small drawdown acceptable due to lag

    def test_drawdown_is_non_positive(self, engine):
        actuals = np.array([100.0, 110.0, 90.0, 95.0, 105.0])
        preds   = np.array([100.0, 108.0, 92.0, 93.0, 103.0])
        m = engine.compute(_make_result(preds, actuals))
        assert m["max_drawdown"] <= 0.0


# ---------------------------------------------------------------------------
# CI width
# ---------------------------------------------------------------------------

class TestCIWidth:
    def test_no_intervals_returns_zero(self, engine):
        preds   = np.array([100.0, 110.0])
        actuals = np.array([100.0, 110.0])
        m = engine.compute(_make_result(preds, actuals, intervals=None))
        assert m["ci_width"] == 0.0

    def test_constant_width(self, engine):
        preds   = np.linspace(100, 200, 10)
        actuals = np.linspace(100, 200, 10)
        intervals = np.column_stack([preds - 5.0, preds + 5.0])
        m = engine.compute(_make_result(preds, actuals, intervals=intervals))
        assert m["ci_width"] == pytest.approx(10.0, rel=1e-4)


# ---------------------------------------------------------------------------
# Empty input guard
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_arrays_raise(self, engine):
        result = ModelResult(
            model_name="EMPTY",
            predictions=np.array([]),
            actuals=np.array([]),
            dates=pd.DatetimeIndex([]),
        )
        with pytest.raises(ValueError):
            engine.compute(result)

    def test_latency_passthrough(self, engine):
        preds   = np.array([100.0, 105.0])
        actuals = np.array([100.0, 105.0])
        m = engine.compute(_make_result(preds, actuals, latency_ms=42.7))
        assert m["latency_ms"] == pytest.approx(42.7, rel=1e-3)
