import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from xgboost import XGBRegressor

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

    feats["target_delta"] = (
        feats["close"].shift(-horizon)
        - feats["close"]
    )

    feats["future_close"] = (
        feats["close"].shift(-horizon)
    )

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    X = feats.drop(
        columns=[
            "target_delta",
            "future_close",
            "date",
        ]
    )

    y_delta = feats["target_delta"]

    current_close = feats["close"]

    future_close = feats["future_close"]

    return (
        X,
        y_delta,
        current_close,
        future_close,
    )


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

    (
        X,
        y_delta,
        current_close,
        future_close,
    ) = build_dataset(
        df,
        horizon,
    )

    total_rows = len(X)

    print(
        f"\nUsable Samples: {total_rows}"
    )

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
        y_train = y_delta.iloc[:train_end]

        X_test = X.iloc[
            train_end:test_end
        ]

        y_test = y_delta.iloc[
            train_end:test_end
        ]

        close_test = current_close.iloc[
            train_end:test_end
        ]

        future_test = future_close.iloc[
            train_end:test_end
        ]

        model = XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
            random_state=42,
        )

        model.fit(
            X_train,
            y_train,
        )

        pred_delta = model.predict(
            X_test
        )

        predicted_price = (
            close_test.values
            + pred_delta
        )

        actual_price = (
            future_test.values
        )

        naive_price = (
            close_test.values
        )

        mae = mean_absolute_error(
            actual_price,
            predicted_price,
        )

        rmse = np.sqrt(
            mean_squared_error(
                actual_price,
                predicted_price,
            )
        )

        r2 = r2_score(
            actual_price,
            predicted_price,
        )

        naive_mae = mean_absolute_error(
            actual_price,
            naive_price,
        )

        actual_direction = np.sign(
            actual_price
            - close_test.values
        )

        pred_direction = np.sign(
            predicted_price
            - close_test.values
        )

        directional_accuracy = (
            actual_direction
            == pred_direction
        ).mean()

        metrics.append(
            {
                "fold": fold,
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "directional_accuracy": directional_accuracy,
                "naive_mae": naive_mae,
            }
        )

        print(
            f"\nFold {fold}"
        )

        print(
            f"MAE                 : {mae:.4f}"
        )

        print(
            f"RMSE                : {rmse:.4f}"
        )

        print(
            f"R²                  : {r2:.4f}"
        )

        print(
            f"Direction Accuracy  : {directional_accuracy:.4f}"
        )

        print(
            f"Naive MAE           : {naive_mae:.4f}"
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
        f"MAE : {results['mae'].mean():.4f}"
    )

    print(
        f"RMSE: {results['rmse'].mean():.4f}"
    )

    print(
        f"R²  : {results['r2'].mean():.4f}"
    )

    print(
        f"Direction Accuracy: "
        f"{results['directional_accuracy'].mean():.4f}"
    )

    print(
        f"Naive MAE: "
        f"{results['naive_mae'].mean():.4f}"
    )

    print("\nStd Dev")
    print("-----------------------------------")

    print(
        f"MAE : {results['mae'].std():.4f}"
    )

    print(
        f"RMSE: {results['rmse'].std():.4f}"
    )

    print(
        f"R²  : {results['r2'].std():.4f}"
    )

    print(
        f"Direction Accuracy: "
        f"{results['directional_accuracy'].std():.4f}"
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