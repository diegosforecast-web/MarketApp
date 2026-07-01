"""
test_compare_engine.py
======================
Integration-style tests for CompareEngine using stub runners.

These tests use a synthetic data loader and monkey-patched runners so they
run in CI with no real model files or network access.

Run with:  pytest comparison/tests/test_compare_engine.py -v
"""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from comparison.compare_engine import CompareConfig, CompareEngine, ModelResult
from comparison.model_runners.base_runner import BaseRunner, PredictOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

N = 300  # number of synthetic OHLCV days


def _synthetic_ohlcv(n: int = N) -> pd.DataFrame:
    """Return a deterministic fake OHLCV DataFrame."""
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(0, 1, n))
    df = pd.DataFrame(
        {
            "open":   close * (1 + rng.uniform(-0.005, 0.005, n)),
            "high":   close * (1 + rng.uniform(0.000, 0.010, n)),
            "low":    close * (1 - rng.uniform(0.000, 0.010, n)),
            "close":  close,
            "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
        },
        index=pd.date_range("2023-01-01", periods=n, freq="B"),
    )
    return df


def _fake_loader(symbol: str, start: str, end: str) -> pd.DataFrame:
    return _synthetic_ohlcv()


class _StubRunner(BaseRunner):
    """Deterministic stub that avoids loading any real model."""

    def _load_model(self):
        return MagicMock()

    def _predict(
        self,
        ohlcv: pd.DataFrame,
        sequence_length: int,
        price_col: str,
    ) -> PredictOutput:
        prices = ohlcv[price_col].values.astype(np.float64)
        _, y = self._build_sequences(prices, sequence_length)
        preds = y * (1 + np.random.default_rng(0).uniform(-0.02, 0.02, len(y)))
        dates = ohlcv.index[sequence_length:]
        return preds, y, dates, None


# ---------------------------------------------------------------------------
# Engine with stubbed runners
# ---------------------------------------------------------------------------

def _make_engine(models_to_stub=None) -> CompareEngine:
    cfg = CompareConfig()
    engine = CompareEngine(config=cfg, data_loader=_fake_loader)
    for name in (models_to_stub or CompareEngine.MODEL_NAMES):
        engine._runners[name] = _StubRunner()
    return engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCompareEngineRun:
    def test_run_returns_all_top_level_keys(self):
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        assert "meta" in result
        assert "ranking" in result
        assert "models" in result
        assert "chart_data" in result
        assert "summary_table" in result

    def test_meta_fields(self):
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("TSLA", "2023-01-01", "2024-01-01")
        )
        assert result["meta"]["symbol"] == "TSLA"
        assert set(result["meta"]["models_run"]) == set(CompareEngine.MODEL_NAMES)

    def test_ranking_has_four_entries(self):
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        assert len(result["ranking"]) == 4

    def test_ranking_is_sorted_by_rank(self):
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        ranks = [r["rank"] for r in result["ranking"]]
        assert ranks == sorted(ranks)

    def test_summary_table_rows_match_model_count(self):
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        assert len(result["summary_table"]) == 4

    def test_partial_models_subset(self):
        engine = _make_engine(["LSTM", "GBM"])
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01", models=["LSTM", "GBM"])
        )
        assert len(result["ranking"]) == 2
        assert set(result["meta"]["models_run"]) == {"LSTM", "GBM"}

    def test_failed_runner_excluded_from_ranking(self):
        engine = _make_engine()

        class _FailingRunner(_StubRunner):
            def _predict(self, ohlcv, sequence_length, price_col):
                raise RuntimeError("Simulated model failure")

        engine._runners["GRU"] = _FailingRunner()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        # GRU should be in failed list, not ranking
        failed_names = [f["model"] for f in result["meta"]["models_failed"]]
        assert "GRU" in failed_names
        ranked_names = [r["model"] for r in result["ranking"]]
        assert "GRU" not in ranked_names

    def test_all_models_fail_raises(self):
        engine = _make_engine()

        class _AlwaysFails(_StubRunner):
            def _predict(self, ohlcv, sequence_length, price_col):
                raise RuntimeError("boom")

        for name in CompareEngine.MODEL_NAMES:
            engine._runners[name] = _AlwaysFails()

        with pytest.raises(RuntimeError, match="All models failed"):
            asyncio.get_event_loop().run_until_complete(
                engine.run("AAPL", "2023-01-01", "2024-01-01")
            )

    def test_result_is_json_serialisable(self):
        import json
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        # Should not raise
        dumped = json.dumps(result)
        assert len(dumped) > 100

    def test_all_metrics_present_per_model(self):
        expected_metrics = {
            "mae", "rmse", "mape", "directional_accuracy",
            "backtest_return", "sharpe_ratio", "max_drawdown",
            "ci_width", "latency_ms",
        }
        engine = _make_engine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run("AAPL", "2023-01-01", "2024-01-01")
        )
        for model_name, model_data in result["models"].items():
            if "error" not in model_data:
                assert expected_metrics.issubset(set(model_data["metrics"].keys())), \
                    f"Missing metrics in {model_name}"
