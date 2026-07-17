"""
ranking.py
==========
Weighted, normalised model ranker.

Algorithm
---------
1. For each metric, collect values across all models.
2. Normalise each metric to [0, 1] so that **higher always means better**:
   - Error metrics (mae, rmse, mape, ci_width, latency_ms):
       normalised = 1 - (val - min) / (max - min)       ← invert
   - Performance metrics (directional_accuracy, backtest_return, sharpe):
       normalised = (val - min) / (max - min)            ← as-is
3. Compute weighted sum → composite score.
4. Rank by composite score (descending).
5. Emit per-model score breakdown and overall rank.

The weight dict is fully configurable via CompareConfig.ranking_weights.
Keys not present in the metric output are silently ignored.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Metrics where lower raw value = better model
_LOWER_IS_BETTER = frozenset({
    "mae",
    "rmse",
    "mape",
    "ci_width",
    "latency_ms",
})
# max_drawdown is negative; less-negative values are better.
# It therefore uses the standard higher-is-better normalization.


class ModelRanker:
    """
    Rank models by a weighted composite of normalised metrics.

    Parameters
    ----------
    weights : dict[str, float]
        Metric name → weight.  Weights need not sum to 1;
        they are re-normalised internally.
    """

    def __init__(self, weights: Dict[str, float]) -> None:
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("Ranking weights must sum to a positive number.")
        self.weights: Dict[str, float] = {k: v / total for k, v in weights.items()}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def rank(
        self, metrics_map: Dict[str, Dict[str, float]]
    ) -> List[Dict]:
        """
        Parameters
        ----------
        metrics_map : {model_name: {metric_name: float}}

        Returns
        -------
        List of dicts sorted by composite_score descending:
        [
          {
            "rank": 1,
            "model": "GBM",
            "composite_score": 0.812,
            "metric_scores": {"mae": 0.9, "sharpe_ratio": 0.75, ...},
          },
          ...
        ]
        """
        model_names = list(metrics_map.keys())
        if not model_names:
            return []

        normalised = self._normalise(metrics_map)
        composite = self._weighted_composite(model_names, normalised)

        ranked = sorted(
            model_names, key=lambda m: composite[m], reverse=True
        )

        results = []
        for rank_idx, name in enumerate(ranked, start=1):
            results.append({
                "rank": rank_idx,
                "model": name,
                "composite_score": round(composite[name], 4),
                "metric_scores": {
                    k: round(v, 4)
                    for k, v in normalised[name].items()
                },
            })
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _normalise(
        self, metrics_map: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Normalise every metric across models to [0, 1],
        direction-corrected so higher = better.
        """
        all_metrics = {
            m for model_metrics in metrics_map.values()
            for m in model_metrics
        }

        normalised: Dict[str, Dict[str, float]] = {
            name: {} for name in metrics_map
        }

        for metric in all_metrics:
            vals = {
                name: metrics_map[name][metric]
                for name in metrics_map
                if metric in metrics_map[name]
            }
            if not vals:
                continue

            lo = min(vals.values())
            hi = max(vals.values())
            span = hi - lo

            for name, val in vals.items():
                if span < 1e-12:
                    # All models tied on this metric
                    norm = 1.0
                elif metric in _LOWER_IS_BETTER:
                    norm = 1.0 - (val - lo) / span
                else:
                    norm = (val - lo) / span
                normalised[name][metric] = float(np.clip(norm, 0.0, 1.0))

        return normalised

    def _weighted_composite(
        self,
        model_names: List[str],
        normalised: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        composite: Dict[str, float] = {}
        for name in model_names:
            score = 0.0
            weight_used = 0.0
            for metric, weight in self.weights.items():
                if metric in normalised[name]:
                    score += normalised[name][metric] * weight
                    weight_used += weight
            # If some metrics were missing, rescale to available weights
            if weight_used > 0:
                composite[name] = score / weight_used
            else:
                composite[name] = 0.0
        return composite
