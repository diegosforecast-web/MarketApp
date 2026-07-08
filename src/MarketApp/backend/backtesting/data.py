"""
Backtesting data utilities for DiMarket.

Purpose
-------
Load price history and build the threshold-direction dataset.

Why it matters
--------------
Separating data preparation from the walk-forward engine keeps the backtesting
pipeline easier to audit, test, and reuse.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from features.engineered_features import build_14_feature_frame


def load_price_data(csv_path: str) -> pd.DataFrame:
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path}"
        )

    df = pd.read_csv(csv_path)

    df.columns = df.columns.str.lower()

    df["date"] = pd.to_datetime(df["date"])

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


def build_threshold_dataset(
    df: pd.DataFrame,
    horizon: int,
    threshold: float,
):
    feats = build_14_feature_frame(df)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    feats["future_close"] = (
        feats["close"]
        .shift(-horizon)
    )

    feats["future_return"] = (
        feats["future_close"]
        / feats["close"]
    ) - 1

    buy_mask = feats["future_return"] > threshold
    sell_mask = feats["future_return"] < -threshold

    feats = feats[
        buy_mask | sell_mask
    ].copy()

    feats["target"] = (
        feats["future_return"] > threshold
    ).astype(int)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    X = feats.drop(
        columns=[
            "target",
            "future_close",
            "future_return",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    y = feats["target"]

    return X, y, feats
