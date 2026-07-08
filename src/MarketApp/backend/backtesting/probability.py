"""
Probability analysis utilities for DiMarket backtests.

Purpose
-------
Analyze model probabilities, confidence thresholds, and probability deciles.

Why it matters
--------------
DiMarket must communicate confidence honestly. These utilities expose how model
probability scores behave across thresholds and buckets.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_CONFIDENCE_THRESHOLDS = [
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


def top_bucket_win_rate(
    probs,
    actuals,
    pct,
):
    count = max(
        1,
        int(len(probs) * pct),
    )

    idx = np.argsort(probs)[::-1][:count]

    return actuals.iloc[idx].mean()


def probability_deciles(
    probs,
    actuals,
) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "prob": probs,
            "actual": actuals.values,
        }
    )

    df["decile"] = pd.qcut(
        df["prob"],
        10,
        labels=False,
        duplicates="drop",
    )

    rows = []

    for d in sorted(
        df["decile"].unique(),
        reverse=True,
    ):
        bucket = df[
            df["decile"] == d
        ]

        rows.append(
            {
                "decile": int(d),
                "count": len(bucket),
                "avg_prob": bucket["prob"].mean(),
                "win_rate": bucket["actual"].mean(),
            }
        )

    return pd.DataFrame(rows)


def confidence_analysis(
    probs,
    actuals,
    thresholds=None,
) -> pd.DataFrame:
    if thresholds is None:
        thresholds = DEFAULT_CONFIDENCE_THRESHOLDS

    rows = []

    for threshold in thresholds:
        mask = probs >= threshold
        trades = int(mask.sum())
        coverage = trades / len(probs)

        if trades == 0:
            win_rate = np.nan
        else:
            win_rate = actuals[mask].mean()

        rows.append(
            {
                "threshold": threshold,
                "trades": trades,
                "coverage": coverage,
                "win_rate": win_rate,
            }
        )

    return pd.DataFrame(rows)
