"""
CLI entry point for threshold-direction walk-forward validation.

Purpose
-------
Run the complete threshold-direction validation workflow.

Why it matters
--------------
This script remains the developer-facing command for validating whether the
current model behavior supports DiMarket's trust-first mission.
"""

from __future__ import annotations

import argparse

from backtesting.data import (
    build_threshold_dataset,
    load_price_data,
)

from backtesting.engine import run_walk_forward_engine
from backtesting.reporting import (
    print_global_reports,
    print_walk_forward_summary,
)


def run_walk_forward(
    csv_path: str,
    horizon: int,
    threshold: float,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
) -> None:
    print(f"\nLoading data from: {csv_path}")

    df = load_price_data(
        csv_path,
    )

    print("\nBuilding threshold dataset...")

    X, y, feats = build_threshold_dataset(
        df=df,
        horizon=horizon,
        threshold=threshold,
    )

    print(f"\nThreshold: {threshold:.2%}")
    print(f"Transaction Cost: {transaction_cost_bps:.2f} bps")
    print(f"Slippage        : {slippage_bps:.2f} bps")
    print(f"Total Cost      : {transaction_cost_bps + slippage_bps:.2f} bps")
    print(f"Usable Samples: {len(X)}")

    print("\nClass Distribution")
    print(y.value_counts())

    result = run_walk_forward_engine(
        X=X,
        y=y,
        feats=feats,
    )

    print_walk_forward_summary(
        result.fold_metrics,
    )

    print_global_reports(
        all_probs=result.all_probs,
        all_actuals=result.all_actuals,
        all_future_returns=result.all_future_returns,
        all_future_dates=result.all_future_dates,
        initial_capital=initial_capital,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
    )


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
    )

    parser.add_argument(
        "--horizon",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.02,
    )

    parser.add_argument(
        "--initial-capital",
        type=float,
        default=100_000.0,
    )

    parser.add_argument(
        "--transaction-cost-bps",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=5.0,
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_walk_forward(
        csv_path=args.csv,
        horizon=args.horizon,
        threshold=args.threshold,
        initial_capital=args.initial_capital,
        transaction_cost_bps=args.transaction_cost_bps,
        slippage_bps=args.slippage_bps,
    )
