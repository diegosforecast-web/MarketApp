from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from training.training_gbm import (
    build_dataset,
    load_price_data,
)


def run_walk_forward(
    *,
    csv_path: str,
    horizon: int,
    initial_train_size: int = 1500,
    test_size: int = 100,
) -> None:
    print(f"\nLoading data from: {csv_path}")

    df = load_price_data(csv_path)
    X, y_log_return = build_dataset(df, horizon)

    if len(X) <= initial_train_size:
        raise ValueError(
            f"Not enough rows ({len(X)}) for initial_train_size="
            f"{initial_train_size}."
        )

    current_close = X["close"].copy()
    actual_simple_return = np.expm1(y_log_return)

    rows: list[dict] = []
    fold = 1
    start = initial_train_size

    while start + test_size <= len(X):
        train_end = start
        test_end = start + test_size

        X_train = X.iloc[:train_end]
        y_train = y_log_return.iloc[:train_end]

        X_test = X.iloc[train_end:test_end]
        y_test_log = y_log_return.iloc[train_end:test_end]
        close_test = current_close.iloc[train_end:test_end]
        actual_return_test = actual_simple_return.iloc[
            train_end:test_end
        ]

        model = GradientBoostingRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.9,
            random_state=42,
        )
        model.fit(X_train, y_train)

        predicted_log_return = model.predict(X_test)
        predicted_return = np.expm1(predicted_log_return)

        predicted_price = (
            close_test.to_numpy() * (1 + predicted_return)
        )
        actual_price = (
            close_test.to_numpy()
            * (1 + actual_return_test.to_numpy())
        )
        naive_price = close_test.to_numpy()

        price_mae = mean_absolute_error(
            actual_price,
            predicted_price,
        )
        price_rmse = np.sqrt(
            mean_squared_error(
                actual_price,
                predicted_price,
            )
        )
        price_r2 = r2_score(
            actual_price,
            predicted_price,
        )
        naive_price_mae = mean_absolute_error(
            actual_price,
            naive_price,
        )

        return_mae = mean_absolute_error(
            actual_return_test,
            predicted_return,
        )
        return_rmse = np.sqrt(
            mean_squared_error(
                actual_return_test,
                predicted_return,
            )
        )
        return_r2 = r2_score(
            actual_return_test,
            predicted_return,
        )

        directional_accuracy = float(
            (
                np.sign(actual_return_test.to_numpy())
                == np.sign(predicted_return)
            ).mean()
        )

        beats_naive = price_mae < naive_price_mae

        rows.append(
            {
                "fold": fold,
                "price_mae": float(price_mae),
                "naive_price_mae": float(naive_price_mae),
                "beats_naive": bool(beats_naive),
                "price_rmse": float(price_rmse),
                "price_r2": float(price_r2),
                "return_mae": float(return_mae),
                "return_rmse": float(return_rmse),
                "return_r2": float(return_r2),
                "directional_accuracy": directional_accuracy,
            }
        )

        print(f"\nFold {fold}")
        print(f"Price MAE           : {price_mae:.4f}")
        print(f"Naive Price MAE     : {naive_price_mae:.4f}")
        print(f"Beats Naive         : {beats_naive}")
        print(f"Price RMSE          : {price_rmse:.4f}")
        print(f"Price R2            : {price_r2:.4f}")
        print(f"Return MAE          : {return_mae:.4f}")
        print(f"Return RMSE         : {return_rmse:.4f}")
        print(f"Return R2           : {return_r2:.4f}")
        print(
            "Directional Accuracy: "
            f"{directional_accuracy:.4f}"
        )

        fold += 1
        start += test_size

    results = pd.DataFrame(rows)

    if results.empty:
        raise ValueError(
            "No walk-forward folds were produced. "
            "Reduce initial_train_size or test_size."
        )

    print("\n===================================")
    print("GBM WALK-FORWARD SUMMARY")
    print("===================================")
    print(results.to_string(index=False))

    print("\nAverage Metrics")
    print("-----------------------------------")
    print(
        f"Price MAE           : "
        f"{results['price_mae'].mean():.4f}"
    )
    print(
        f"Naive Price MAE     : "
        f"{results['naive_price_mae'].mean():.4f}"
    )
    print(
        f"Folds Beating Naive : "
        f"{int(results['beats_naive'].sum())}/{len(results)}"
    )
    print(
        f"Price RMSE          : "
        f"{results['price_rmse'].mean():.4f}"
    )
    print(
        f"Price R2            : "
        f"{results['price_r2'].mean():.4f}"
    )
    print(
        f"Return MAE          : "
        f"{results['return_mae'].mean():.4f}"
    )
    print(
        f"Return RMSE         : "
        f"{results['return_rmse'].mean():.4f}"
    )
    print(
        f"Return R2           : "
        f"{results['return_r2'].mean():.4f}"
    )
    print(
        f"Directional Accuracy: "
        f"{results['directional_accuracy'].mean():.4f}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--initial-train-size",
        type=int,
        default=1500,
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=100,
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_walk_forward(
        csv_path=args.csv,
        horizon=args.horizon,
        initial_train_size=args.initial_train_size,
        test_size=args.test_size,
    )
