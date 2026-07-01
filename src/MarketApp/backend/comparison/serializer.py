"""
serializer.py
=============
Transforms raw ModelResults + computed metrics into a single,
frontend-ready JSON-serialisable dict.

Output schema (top-level keys)
-------------------------------
  meta          – run metadata (symbol, dates, generated_at, models_run)
  ranking       – ordered list of model rank objects (from ModelRanker)
  models        – per-model detail block (metrics, chart series, latency)
  chart_data    – unified cross-model chart series for the frontend
  summary_table – flat list of rows for a comparison table widget

All floats are rounded to 6 dp; numpy scalars are cast to native Python types
so the dict is directly JSON-serialisable via json.dumps / FastAPI's JSONResponse.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .metrics import rolling_directional_accuracy

logger = logging.getLogger(__name__)

# Metrics to surface in the summary table, in display order
_TABLE_METRICS = [
    ("mae",                  "MAE",                  "price",   False),
    ("rmse",                 "RMSE",                 "price",   False),
    ("mape",                 "MAPE (%)",              "percent", False),
    ("directional_accuracy", "Dir. Accuracy (%)",     "percent", True),
    ("backtest_return",      "Backtest Return",       "percent", True),
    ("sharpe_ratio",         "Sharpe Ratio",          "ratio",   True),
    ("max_drawdown",         "Max Drawdown",          "percent", False),
    ("ci_width",             "CI Width",              "price",   False),
    ("latency_ms",           "Latency (ms)",          "ms",      False),
]

_CHART_MAX_POINTS = 500  # downsample if series is longer


class ComparisonSerializer:
    """Convert engine outputs into a single frontend-ready payload."""

    def build(
        self,
        symbol: str,
        start: str,
        end: str,
        raw_results: List[Any],          # List[ModelResult]
        metrics_map: Dict[str, Dict[str, float]],
        ranking: List[Dict],
    ) -> Dict[str, Any]:

        models_block = self._build_models_block(raw_results, metrics_map)
        chart_data   = self._build_chart_data(raw_results)
        summary_table = self._build_summary_table(metrics_map, ranking)

        payload = {
            "meta": {
                "symbol": symbol,
                "start": start,
                "end": end,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "models_run": [r.model_name for r in raw_results if not r.error],
                "models_failed": [
                    {"model": r.model_name, "error": r.error}
                    for r in raw_results if r.error
                ],
            },
            "ranking": ranking,
            "models": models_block,
            "chart_data": chart_data,
            "summary_table": summary_table,
        }

        return _to_serialisable(payload)

    # ------------------------------------------------------------------
    # Per-model block
    # ------------------------------------------------------------------

    def _build_models_block(
        self,
        raw_results: List[Any],
        metrics_map: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        block: Dict[str, Any] = {}
        for result in raw_results:
            name = result.model_name
            if result.error:
                block[name] = {"error": result.error, "latency_ms": result.latency_ms}
                continue

            n = len(result.predictions)
            step = max(1, n // _CHART_MAX_POINTS)

            block[name] = {
                "metrics": metrics_map.get(name, {}),
                "latency_ms": result.latency_ms,
                "series": {
                    "dates":       _to_iso_list(result.dates[::step]),
                    "predictions": _round_list(result.predictions[::step]),
                    "actuals":     _round_list(result.actuals[::step]),
                    "ci_lower": (
                        _round_list(result.prediction_intervals[::step, 0])
                        if result.prediction_intervals is not None else []
                    ),
                    "ci_upper": (
                        _round_list(result.prediction_intervals[::step, 1])
                        if result.prediction_intervals is not None else []
                    ),
                },
                "rolling_dir_accuracy": _build_rolling_dir_acc(result, step),
                "cumulative_returns":   _build_cumulative_returns(result, step),
            }
        return block

    # ------------------------------------------------------------------
    # Cross-model chart data
    # ------------------------------------------------------------------

    def _build_chart_data(self, raw_results: List[Any]) -> Dict[str, Any]:
        """
        Unified cross-model time-series chart payloads.

        Returned keys:
          predictions_overlay  – all models on the same price chart
          sharpe_bar           – bar chart ready [model, sharpe]
          drawdown_area        – area chart of per-model equity curves
          error_scatter        – scatter of (mae, rmse) per model
        """
        # Use the longest successful result as the date reference
        successful = [r for r in raw_results if not r.error and len(r.dates) > 0]
        if not successful:
            return {}

        ref = max(successful, key=lambda r: len(r.dates))
        n = len(ref.dates)
        step = max(1, n // _CHART_MAX_POINTS)
        dates = _to_iso_list(ref.dates[::step])

        predictions_overlay = {"dates": dates, "actuals": _round_list(ref.actuals[::step])}
        drawdown_area = {"dates": dates}

        for result in successful:
            name = result.model_name
            # Align to reference length (truncate / pad with NaN)
            preds = _align(result.predictions, n)[::step]
            actuals = _align(result.actuals, n)[::step]

            predictions_overlay[name] = _round_list(preds)

            # Equity curve from long/short strategy
            strategy_rets = np.sign(np.diff(preds)) * (np.diff(actuals) / (np.abs(actuals[:-1]) + 1e-9))
            equity = np.cumprod(1.0 + np.concatenate([[0.0], strategy_rets]))
            drawdown_area[name] = _round_list(equity)

        return {
            "predictions_overlay": predictions_overlay,
            "drawdown_area": drawdown_area,
        }

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------

    def _build_summary_table(
        self,
        metrics_map: Dict[str, Dict[str, float]],
        ranking: List[Dict],
    ) -> List[Dict[str, Any]]:
        """
        List of row dicts, one per model, ready for a DataGrid component.
        Includes rank, model name, and all key metrics.
        """
        rank_lookup = {r["model"]: r for r in ranking}
        rows = []
        for name, metrics in metrics_map.items():
            rank_info = rank_lookup.get(name, {})
            row: Dict[str, Any] = {
                "rank": rank_info.get("rank", "-"),
                "model": name,
                "composite_score": rank_info.get("composite_score", None),
            }
            for key, label, unit, higher_better in _TABLE_METRICS:
                val = metrics.get(key)
                row[key] = {
                    "value": val,
                    "label": label,
                    "unit": unit,
                    "higher_is_better": higher_better,
                    "formatted": _format_metric(key, val, unit),
                }
            rows.append(row)

        # Sort by rank
        rows.sort(key=lambda r: r["rank"] if isinstance(r["rank"], int) else 999)
        return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_metric(key: str, val: Optional[float], unit: str) -> str:
    if val is None:
        return "N/A"
    if unit == "percent":
        return f"{val:.2f}%"
    if unit == "price":
        return f"{val:.4f}"
    if unit == "ratio":
        return f"{val:.3f}"
    if unit == "ms":
        return f"{val:.1f} ms"
    return f"{val:.4f}"


def _round_list(arr: np.ndarray, dp: int = 4) -> List[float]:
    return [round(float(v), dp) if not np.isnan(v) else None for v in arr]


def _to_iso_list(idx) -> List[str]:
    if isinstance(idx, pd.DatetimeIndex):
        return [str(d.date()) for d in idx]
    return [str(d) for d in idx]


def _align(arr: np.ndarray, target_len: int) -> np.ndarray:
    if len(arr) >= target_len:
        return arr[-target_len:]
    pad = np.full(target_len - len(arr), np.nan)
    return np.concatenate([pad, arr])


def _build_rolling_dir_acc(result: Any, step: int) -> List[Optional[float]]:
    if len(result.predictions) < 2:
        return []
    rda = rolling_directional_accuracy(result.predictions, result.actuals)
    return _round_list(rda[::step], dp=2)


def _build_cumulative_returns(result: Any, step: int) -> List[Optional[float]]:
    if len(result.predictions) < 2:
        return []
    sigs = np.sign(np.diff(result.predictions))
    rets = sigs * (np.diff(result.actuals) / (np.abs(result.actuals[:-1]) + 1e-9))
    cum = np.cumprod(1.0 + rets)
    return _round_list(cum[::step])


def _to_serialisable(obj: Any) -> Any:
    """Recursively convert numpy types → native Python for JSON safety."""
    if isinstance(obj, dict):
        return {k: _to_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serialisable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if np.isnan(v) or np.isinf(v) else v
    if isinstance(obj, np.ndarray):
        return _to_serialisable(obj.tolist())
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    return obj
