"""
Trade analysis utilities for DiMarket backtests.

Purpose
-------
Convert model probabilities and realized future returns into portfolio-level
trade statistics.

Why it matters
--------------
A trustworthy forecast platform must show how signals behave after realistic
costs and slippage, not just raw prediction accuracy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from evaluation.analytics import PortfolioAnalytics


DEFAULT_TRADE_THRESHOLDS = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
]


def trade_analysis(
    probs,
    actuals,
    future_returns,
    future_dates=None,
    initial_capital: float = 100_000.0,
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
    thresholds=None,
):
    if thresholds is None:
        thresholds = DEFAULT_TRADE_THRESHOLDS

    rows = []
    detailed_metrics = {}

    total_cost_bps = transaction_cost_bps + slippage_bps
    total_cost_decimal = total_cost_bps / 10_000.0

    probs = np.asarray(
        probs,
        dtype=float,
    )

    actuals = pd.Series(
        actuals,
    ).reset_index(drop=True)

    future_returns = pd.Series(
        future_returns,
        dtype=float,
    ).reset_index(drop=True)

    if future_dates is not None:
        future_dates = pd.Series(
            pd.to_datetime(future_dates),
        ).reset_index(drop=True)

    for threshold in thresholds:
        mask = probs >= threshold
        trades = int(mask.sum())

        if trades == 0:
            continue

        gross_selected_returns = (
            future_returns[mask]
            .reset_index(drop=True)
        )

        selected_returns = (
            gross_selected_returns
            - total_cost_decimal
        )

        selected_dates = None

        if future_dates is not None:
            selected_dates = (
                future_dates[mask]
                .reset_index(drop=True)
            )

        analytics = PortfolioAnalytics(
            trade_returns=selected_returns,
            dates=selected_dates,
            initial_capital=initial_capital,
        )

        metrics = analytics.calculate()

        detailed_metrics[threshold] = metrics

        rows.append(
            {
                "threshold": threshold,
                "trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "gross_avg_return": gross_selected_returns.mean(),
                "net_avg_return": metrics.average_return,
                "transaction_cost_bps": transaction_cost_bps,
                "slippage_bps": slippage_bps,
                "total_cost_bps": total_cost_bps,
                "total_return": metrics.cumulative_return,
                "profit_factor": metrics.profit_factor,
                "max_drawdown": metrics.max_drawdown,
                "sharpe_ratio": metrics.sharpe_ratio,
                "sortino_ratio": metrics.sortino_ratio,
                "cagr": metrics.cagr,
                "final_equity": metrics.final_equity,
            }
        )

    return pd.DataFrame(rows), detailed_metrics
