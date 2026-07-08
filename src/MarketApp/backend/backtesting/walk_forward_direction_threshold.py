"""
Backward-compatible wrapper for the refactored walk-forward backtest.

Use:
    python -m backtesting.walk_forward
or:
    python -m backtesting.walk_forward_direction_threshold
"""

from __future__ import annotations

from backtesting.walk_forward import (
    parse_args,
    run_walk_forward,
)


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
