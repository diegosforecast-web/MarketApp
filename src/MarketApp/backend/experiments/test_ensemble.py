"""
Integration test for the Ensemble Decision Engine.

Purpose
-------
Verify that DiMarket can load production models from the Model Registry,
run both models on recent market data, and produce a unified decision.
"""

from __future__ import annotations

import argparse

import pandas as pd

from ensemble.decision_engine import EnsembleDecisionEngine


def load_price_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    df.columns = df.columns.str.lower()

    df["date"] = pd.to_datetime(
        df["date"]
    )

    numeric_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    df[numeric_cols] = df[numeric_cols].apply(
        pd.to_numeric,
        errors="coerce",
    )

    return (
        df.sort_values("date")
        .reset_index(drop=True)
    )


def print_decision(decision) -> None:
    print("\n===================================")
    print("DIMARKET ENSEMBLE DECISION")
    print("===================================")

    print(f"Ticker                : {decision.ticker}")
    print(f"Direction Probability : {decision.direction_probability:.2%}")
    print(f"Expected Return       : {decision.expected_return:.2%}")
    print(f"Recommendation        : {decision.recommendation}")
    print(f"Confidence            : {decision.confidence}")

    print("\nReasons")
    print("-------")
    if decision.reasons:
        for reason in decision.reasons:
            print(f"- {reason}")
    else:
        print("- None")

    print("\nWarnings")
    print("--------")
    if decision.warnings:
        for warning in decision.warnings:
            print(f"- {warning}")
    else:
        print("- None")


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
    )

    parser.add_argument(
        "--ticker",
        default="AAPL",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    df = load_price_data(
        args.csv,
    )

    engine = EnsembleDecisionEngine()

    decision = engine.predict(
        ticker=args.ticker,
        price_df=df,
    )

    print_decision(decision)