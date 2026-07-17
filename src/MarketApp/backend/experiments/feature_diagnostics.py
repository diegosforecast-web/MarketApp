"""
Feature diagnostics for the threshold-direction XGBoost model.

Purpose
-------
Measure how much each feature contributes to validation performance by removing
one feature at a time and retraining the model.

Why it matters
--------------
DiMarket should improve model quality using evidence, not guesses.
"""

from __future__ import annotations

import argparse

import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from xgboost import XGBClassifier

from training.training_direction_threshold import (
    build_dataset,
    load_price_data,
)


def train_and_score(
    X: pd.DataFrame,
    y: pd.Series,
) -> dict:
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.20,
        shuffle=False,
    )

    positives = (y_train == 1).sum()
    negatives = (y_train == 0).sum()

    scale_pos_weight = negatives / positives

    model = XGBClassifier(
        n_estimators=1000,
        max_depth=4,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
    )

    model.fit(
        X_train,
        y_train,
    )

    probabilities = model.predict_proba(X_val)[:, 1]
    pred = (probabilities >= 0.50).astype(int)

    ranking = pd.DataFrame(
        {
            "probability": probabilities,
            "actual": y_val.values,
        }
    ).sort_values(
        "probability",
        ascending=False,
    )

    return {
        "accuracy": accuracy_score(y_val, pred),
        "precision": precision_score(y_val, pred, zero_division=0),
        "recall": recall_score(y_val, pred, zero_division=0),
        "f1": f1_score(y_val, pred, zero_division=0),
        "auc": roc_auc_score(y_val, probabilities),
        "top10": ranking.head(10)["actual"].mean(),
        "top20": ranking.head(20)["actual"].mean(),
        "top30": ranking.head(30)["actual"].mean(),
    }


def run_feature_diagnostics(
    csv_path: str,
    horizon: int,
    threshold: float,
    output_csv: str,
) -> pd.DataFrame:
    print(f"\nLoading data from: {csv_path}")

    df = load_price_data(csv_path)

    print("\nBuilding threshold dataset...")

    X, y = build_dataset(
        df=df,
        horizon=horizon,
        threshold=threshold,
    )

    print("\nTraining baseline model...")

    baseline = train_and_score(
        X,
        y,
    )

    print("\nBaseline Metrics")
    print("----------------")
    for key, value in baseline.items():
        print(f"{key:<10}: {value:.4f}")

    rows = []

    for feature in X.columns:
        print(f"\nTesting without feature: {feature}")

        X_reduced = X.drop(
            columns=[feature],
        )

        scores = train_and_score(
            X_reduced,
            y,
        )

        row = {
            "removed_feature": feature,
            "baseline_accuracy": baseline["accuracy"],
            "accuracy": scores["accuracy"],
            "delta_accuracy": scores["accuracy"] - baseline["accuracy"],
            "baseline_f1": baseline["f1"],
            "f1": scores["f1"],
            "delta_f1": scores["f1"] - baseline["f1"],
            "baseline_auc": baseline["auc"],
            "auc": scores["auc"],
            "delta_auc": scores["auc"] - baseline["auc"],
            "baseline_top20": baseline["top20"],
            "top20": scores["top20"],
            "delta_top20": scores["top20"] - baseline["top20"],
        }

        rows.append(row)

    results = (
        pd.DataFrame(rows)
        .sort_values(
            "delta_f1",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print("\n===================================")
    print("FEATURE DIAGNOSTICS")
    print("===================================")

    print(
        results[
            [
                "removed_feature",
                "delta_accuracy",
                "delta_f1",
                "delta_auc",
                "delta_top20",
            ]
        ].to_string(index=False)
    )

    results.to_csv(
        output_csv,
        index=False,
    )

    print(f"\nFeature diagnostics saved to: {output_csv}")

    return results


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
        "--out",
        default="reports/feature_diagnostics.csv",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_feature_diagnostics(
        csv_path=args.csv,
        horizon=args.horizon,
        threshold=args.threshold,
        output_csv=args.out,
    )