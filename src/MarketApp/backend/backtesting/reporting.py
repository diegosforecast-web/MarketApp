"""
Console reporting utilities for DiMarket backtests.

Purpose
-------
Centralize backtest output formatting.

Why it matters
--------------
Reports are part of user trust. Keeping output formatting in one place makes
results easier to audit and prevents hidden metric drift.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from evaluation.analytics import summarize_portfolio_metrics
from evaluation.calibration import (
    CalibrationAnalyzer,
    compare_probability_calibrators,
    summarize_calibration_comparison,
    summarize_calibration_metrics,
)

from backtesting.probability import confidence_analysis
from backtesting.trade_analysis import trade_analysis


def print_walk_forward_summary(
    results: pd.DataFrame,
) -> None:
    print("\n===================================")
    print("WALK FORWARD SUMMARY")
    print("===================================")
    print(results)

    print("\nAverage Metrics")
    print("-----------------------------------")
    print(f"Accuracy : {results['accuracy'].mean():.4f}")
    print(f"Precision: {results['precision'].mean():.4f}")
    print(f"Recall   : {results['recall'].mean():.4f}")
    print(f"F1 Score : {results['f1'].mean():.4f}")
    print(f"Baseline : {results['baseline'].mean():.4f}")
    print(f"Top10 WR : {results['top10'].mean():.4f}")
    print(f"Top20 WR : {results['top20'].mean():.4f}")
    print(f"Top30 WR : {results['top30'].mean():.4f}")


def print_global_reports(
    *,
    all_probs,
    all_actuals,
    all_future_returns,
    all_future_dates,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
) -> None:
    print("\n===================================")
    print("GLOBAL CONFIDENCE ANALYSIS")
    print("===================================")

    global_conf = confidence_analysis(
        np.array(all_probs),
        pd.Series(all_actuals),
    )

    print(global_conf)

    calibration = CalibrationAnalyzer(
        probabilities=np.array(all_probs),
        actuals=pd.Series(all_actuals),
        n_bins=10,
    ).calculate()

    print(
        summarize_calibration_metrics(
            calibration,
        )
    )

    print("\nReliability Table")
    print(calibration.reliability_table)

    calibration_comparison = compare_probability_calibrators(
        probabilities=np.array(all_probs),
        actuals=pd.Series(all_actuals),
        n_bins=10,
        calibration_fraction=0.60,
    )

    print(
        summarize_calibration_comparison(
            calibration_comparison,
        )
    )

    print(
        calibration_comparison.comparison_table
    )

    print("\n===================================")
    print("GLOBAL TRADE ANALYSIS")
    print("===================================")

    trade_stats, detailed_metrics = trade_analysis(
        probs=np.array(all_probs),
        actuals=pd.Series(all_actuals),
        future_returns=pd.Series(all_future_returns),
        future_dates=pd.Series(all_future_dates),
        initial_capital=initial_capital,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
    )

    print(trade_stats)

    if trade_stats.empty:
        return

    best_row = trade_stats.sort_values(
        "profit_factor",
        ascending=False,
    ).iloc[0]

    best_threshold = float(
        best_row["threshold"],
    )

    print("\n===================================")
    print("BEST THRESHOLD PORTFOLIO REPORT")
    print("===================================")
    print(f"Selected Threshold: {best_threshold:.2f}")

    print(
        summarize_portfolio_metrics(
            detailed_metrics[best_threshold],
        )
    )
