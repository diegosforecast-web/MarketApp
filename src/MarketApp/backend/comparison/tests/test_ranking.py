"""
test_ranking.py
===============
Unit tests for ModelRanker.

Run with:  pytest comparison/tests/test_ranking.py -v
"""

from __future__ import annotations

import pytest
from comparison.ranking import ModelRanker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {
    "mae":                  0.10,
    "rmse":                 0.10,
    "mape":                 0.10,
    "directional_accuracy": 0.15,
    "backtest_return":      0.20,
    "sharpe_ratio":         0.20,
    "max_drawdown":         0.10,
    "ci_width":             0.05,
}


@pytest.fixture()
def ranker():
    return ModelRanker(DEFAULT_WEIGHTS)


# ---------------------------------------------------------------------------
# Basic ranking
# ---------------------------------------------------------------------------

class TestBasicRanking:
    def test_better_model_ranked_first(self, ranker):
        metrics = {
            "GOOD": {
                "mae": 1.0, "rmse": 1.5, "mape": 0.5,
                "directional_accuracy": 80.0,
                "backtest_return": 0.30, "sharpe_ratio": 2.5,
                "max_drawdown": -0.05, "ci_width": 2.0,
            },
            "BAD": {
                "mae": 10.0, "rmse": 15.0, "mape": 5.0,
                "directional_accuracy": 45.0,
                "backtest_return": -0.10, "sharpe_ratio": -0.5,
                "max_drawdown": -0.40, "ci_width": 20.0,
            },
        }
        result = ranker.rank(metrics)
        assert result[0]["model"] == "GOOD"
        assert result[1]["model"] == "BAD"

    def test_rank_field_is_1_indexed(self, ranker):
        metrics = {
            "A": {"mae": 1.0, "sharpe_ratio": 2.0},
            "B": {"mae": 5.0, "sharpe_ratio": 0.5},
        }
        result = ranker.rank(metrics)
        ranks = [r["rank"] for r in result]
        assert ranks == [1, 2]

    def test_composite_score_between_0_and_1(self, ranker):
        metrics = {
            "M1": {"mae": 2.0, "sharpe_ratio": 1.5, "directional_accuracy": 60.0},
            "M2": {"mae": 4.0, "sharpe_ratio": 0.8, "directional_accuracy": 52.0},
        }
        result = ranker.rank(metrics)
        for r in result:
            assert 0.0 <= r["composite_score"] <= 1.0

    def test_all_models_tied_same_score(self, ranker):
        m = {"mae": 5.0, "sharpe_ratio": 1.0}
        metrics = {"A": m.copy(), "B": m.copy(), "C": m.copy()}
        result = ranker.rank(metrics)
        scores = [r["composite_score"] for r in result]
        # All tied → all should be 1.0 (single model per metric, span=0)
        assert all(s == pytest.approx(1.0, abs=1e-6) for s in scores)

    def test_single_model(self, ranker):
        metrics = {"SOLO": {"mae": 3.0, "sharpe_ratio": 1.2}}
        result = ranker.rank(metrics)
        assert len(result) == 1
        assert result[0]["rank"] == 1

    def test_empty_metrics_map(self, ranker):
        assert ranker.rank({}) == []


# ---------------------------------------------------------------------------
# Weights validation
# ---------------------------------------------------------------------------

class TestWeightsValidation:
    def test_zero_weights_raise(self):
        with pytest.raises(ValueError):
            ModelRanker({"mae": 0.0, "sharpe_ratio": 0.0})

    def test_negative_total_raise(self):
        with pytest.raises(ValueError):
            ModelRanker({"mae": -1.0})

    def test_weights_are_renormalised(self):
        # Weights sum to 2.0 – should be treated as if they sum to 1.0
        r = ModelRanker({"mae": 1.0, "sharpe_ratio": 1.0})
        assert abs(sum(r.weights.values()) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Missing metric handling
# ---------------------------------------------------------------------------

class TestMissingMetrics:
    def test_missing_metric_in_one_model(self, ranker):
        metrics = {
            "A": {"mae": 1.0, "sharpe_ratio": 2.0, "directional_accuracy": 70.0},
            "B": {"mae": 3.0, "sharpe_ratio": 1.0},  # no directional_accuracy
        }
        # Should not raise; B just misses that metric in its score
        result = ranker.rank(metrics)
        assert len(result) == 2

    def test_metric_scores_contain_only_available_metrics(self, ranker):
        metrics = {
            "A": {"mae": 1.0},
            "B": {"mae": 3.0},
        }
        result = ranker.rank(metrics)
        for r in result:
            assert "mae" in r["metric_scores"]


# ---------------------------------------------------------------------------
# Direction correctness
# ---------------------------------------------------------------------------

class TestDirectionCorrectness:
    def test_lower_mae_model_has_higher_mae_score(self):
        ranker = ModelRanker({"mae": 1.0})
        metrics = {
            "LOW_MAE":  {"mae": 1.0},
            "HIGH_MAE": {"mae": 10.0},
        }
        result = ranker.rank(metrics)
        scores = {r["model"]: r["metric_scores"]["mae"] for r in result}
        assert scores["LOW_MAE"] > scores["HIGH_MAE"]

    def test_higher_sharpe_model_has_higher_sharpe_score(self):
        ranker = ModelRanker({"sharpe_ratio": 1.0})
        metrics = {
            "LOW_SHARPE":  {"sharpe_ratio": 0.5},
            "HIGH_SHARPE": {"sharpe_ratio": 3.0},
        }
        result = ranker.rank(metrics)
        scores = {r["model"]: r["metric_scores"]["sharpe_ratio"] for r in result}
        assert scores["HIGH_SHARPE"] > scores["LOW_SHARPE"]

    def test_less_negative_drawdown_scores_higher(self):
        ranker = ModelRanker({"max_drawdown": 1.0})
        metrics = {
            "SHALLOW": {"max_drawdown": -0.05},
            "DEEP":    {"max_drawdown": -0.50},
        }
        result = ranker.rank(metrics)
        scores = {r["model"]: r["metric_scores"]["max_drawdown"] for r in result}
        assert scores["SHALLOW"] > scores["DEEP"]
