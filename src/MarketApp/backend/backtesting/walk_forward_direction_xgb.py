import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from xgboost import XGBClassifier

from features.engineered_features import (
    build_14_feature_frame,
)


# ==========================================================
# DATA LOADING
# ==========================================================
def load_price_data(csv_path: str) -> pd.DataFrame:

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path}"
        )

    df = pd.read_csv(csv_path)

    df.columns = (
        df.columns
        .str.lower()
    )

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

    df[numeric_cols] = df[
        numeric_cols
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    df = (
        df.sort_values("date")
        .reset_index(drop=True)
    )

    return df


# ==========================================================
# DATASET BUILDER
# ==========================================================
def build_dataset(
    df: pd.DataFrame,
    horizon: int,
):
    feats = build_14_feature_frame(df)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    future_close = (
        feats["close"]
        .shift(-horizon)
    )

    feats["target"] = (
        future_close > feats["close"]
    ).astype(int)

    feats["future_close"] = future_close

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    X = feats.drop(
        columns=[
            "target",
            "future_close",
            "date",
        ]
    )

    y = feats["target"]

    return X, y, feats


# ==========================================================
# WALK FORWARD TEST
# ==========================================================
def run_walk_forward(
    csv_path: str,
    horizon: int,
):
    print(
        f"\nLoading data from: {csv_path}"
    )

    df = load_price_data(csv_path)

    print(
        "\nBuilding feature dataset..."
    )

    X, y, feats = build_dataset(
        df,
        horizon,
    )

    total_rows = len(X)

    print(
        f"\nUsable Samples: {total_rows}"
    )

    # ----------------------------------
    # Walk-forward parameters
    # ----------------------------------

    train_size = 1500
    test_size = 100

    fold = 1

    metrics = []

    start = train_size

    while (
        start + test_size
        <= total_rows
    ):
        train_end = start
        test_end = start + test_size

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        X_test = X.iloc[
            train_end:test_end
        ]

        y_test = y.iloc[
            train_end:test_end
        ]

        model = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="logloss",
        )

        model.fit(
            X_train,
            y_train,
        )

        pred = model.predict(
            X_test
        )

        accuracy = accuracy_score(
            y_test,
            pred,
        )

        precision = precision_score(
            y_test,
            pred,
            zero_division=0,
        )

        recall = recall_score(
            y_test,
            pred,
            zero_division=0,
        )

        f1 = f1_score(
            y_test,
            pred,
            zero_division=0,
        )

        metrics.append(
            {
                "fold": fold,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )

        print(
            f"\nFold {fold}"
        )

        print(
            f"Accuracy : {accuracy:.4f}"
        )

        print(
            f"Precision: {precision:.4f}"
        )

        print(
            f"Recall   : {recall:.4f}"
        )

        print(
            f"F1 Score : {f1:.4f}"
        )

        fold += 1

        start += test_size

    results = pd.DataFrame(
        metrics
    )

    print("\n===================================")
    print("WALK FORWARD SUMMARY")
    print("===================================")

    print(results)

    print("\nAverage Metrics")
    print("-----------------------------------")

    print(
        f"Accuracy : {results['accuracy'].mean():.4f}"
    )

    print(
        f"Precision: {results['precision'].mean():.4f}"
    )

    print(
        f"Recall   : {results['recall'].mean():.4f}"
    )

    print(
        f"F1 Score : {results['f1'].mean():.4f}"
    )

    print("\nStd Dev")
    print("-----------------------------------")

    print(
        f"Accuracy : {results['accuracy'].std():.4f}"
    )

    print(
        f"Precision: {results['precision'].std():.4f}"
    )

    print(
        f"Recall   : {results['recall'].std():.4f}"
    )

    print(
        f"F1 Score : {results['f1'].std():.4f}"
    )


# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":

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

    args = parser.parse_args()

    run_walk_forward(
        csv_path=args.csv,
        horizon=args.horizon,
    )