"""
DiMarket Feature Audit

Usage:
    python -m diagnostics.feature_audit

This script analyzes the engineered feature set used by the GBM model.

It reports:

- Dataset summary
- Missing values
- Constant features
- Low variance features
- Highly correlated features
- Correlation matrix (saved)
- Feature importance (saved if model exists)
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from features.engineered_features import build_14_feature_frame


DATA_PATH = Path("data") / "price_history.csv"
MODEL_PATH = Path("models") / "gbm_model.pkl"
REPORT_PATH = Path("reports")


def header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def section(title: str):
    print("\n" + title)
    print("-" * 50)


def load_features():

    df = pd.read_csv(DATA_PATH)

    df.columns = df.columns.str.lower()

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date").reset_index(drop=True)

    feats = build_14_feature_frame(df)

    feats = feats.dropna().reset_index(drop=True)

    return feats


def main():

    REPORT_PATH.mkdir(exist_ok=True)

    feats = load_features()

    header("DiMarket Feature Audit")

    section("Dataset")

    print(f"Rows     : {len(feats):,}")
    print(f"Columns  : {len(feats.columns)}")

    features = feats.drop(columns=["date"])

    section("Missing Values")

    missing = features.isna().sum()

    if missing.sum() == 0:
        print("No missing values.")
    else:
        print(missing[missing > 0])

    section("Constant Features")

    constant = [
        c for c in features.columns
        if features[c].nunique() <= 1
    ]

    if constant:
        for c in constant:
            print(c)
    else:
        print("None")

    section("Low Variance Features")

    variance = features.var(numeric_only=True)

    low_variance = variance[variance < 1e-6]

    if len(low_variance):
        print(low_variance)
    else:
        print("None")

    section("Feature Correlation")

    corr = features.corr(numeric_only=True)

    corr.to_csv(REPORT_PATH / "feature_correlation.csv")

    high_corr = []

    cols = corr.columns

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            value = corr.iloc[i, j]

            if abs(value) >= 0.95:
                high_corr.append(
                    (
                        cols[i],
                        cols[j],
                        value,
                    )
                )

    if high_corr:

        high_corr = sorted(
            high_corr,
            key=lambda x: abs(x[2]),
            reverse=True,
        )

        for a, b, c in high_corr:
            print(f"{a:20} {b:20} {c:.4f}")

    else:
        print("No highly correlated features.")

    section("Feature Importance")

    if MODEL_PATH.exists():

        bundle = joblib.load(MODEL_PATH)

        model = bundle["model"]

        importance = pd.DataFrame(
            {
                "Feature": features.columns,
                "Importance": model.feature_importances_,
            }
        )

        importance = importance.sort_values(
            "Importance",
            ascending=False,
        )

        print(importance)

        importance.to_csv(
            REPORT_PATH / "feature_importance.csv",
            index=False,
        )

    else:
        print("Model not found.")

    section("Recommendations")

    print("Review highly correlated features.")
    print("Check whether OHLC dominates the model.")
    print("Consider adding lag features.")
    print("Evaluate predicting returns instead of price.")
    print("Use importance rankings before removing features.")

    header("Audit Complete")


if __name__ == "__main__":
    main()