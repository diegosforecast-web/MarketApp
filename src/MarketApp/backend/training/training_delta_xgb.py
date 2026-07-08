import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split

from xgboost import XGBRegressor

from features.engineered_features import build_14_feature_frame


def load_price_data(csv_path: str) -> pd.DataFrame:
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path}"
        )

    df = pd.read_csv(csv_path)

    df.columns = df.columns.str.lower()

    print("\n==============================")
    print("Dataset Preview")
    print("==============================")
    print(df.head())

    print("\nColumns:")
    print(df.columns.tolist())

    print(f"\nDataset Shape: {df.shape}")

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

    df = (
        df.sort_values("date")
        .reset_index(drop=True)
    )

    return df


def build_dataset(
    df: pd.DataFrame,
    horizon: int,
):
    feats = build_14_feature_frame(df)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    print(
        f"\nFeature frame shape: "
        f"{feats.shape}"
    )

    # -------------------------------------
    # DELTA TARGET
    # -------------------------------------
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

    print("\nTarget Alignment Preview")
    print("------------------------")

    print(
        feats[
            [
                "date",
                "close",
                "future_close",
                "target_delta",
            ]
        ].head(10)
    )

    X = feats.drop(
        columns=[
            "target_delta",
            "future_close",
            "date",
        ]
    )

    y_delta = feats["target_delta"]

    future_close = feats["future_close"]

    current_close = feats["close"]

    return (
        X,
        y_delta,
        current_close,
        future_close,
    )


def train_delta_xgb(
    csv_path: str,
    model_out: str,
    horizon: int,
):
    print(
        f"\nLoading data from: "
        f"{csv_path}"
    )

    df = load_price_data(csv_path)

    print(
        "\nBuilding engineered feature dataset..."
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

    print(
        f"\nUsable samples: "
        f"{len(X)}"
    )

    (
        X_train,
        X_val,
        y_train,
        y_val,
        close_train,
        close_val,
        future_train,
        future_val,
    ) = train_test_split(
        X,
        y_delta,
        current_close,
        future_close,
        test_size=0.20,
        shuffle=False,
    )

    print("\nTrain / Validation Split")
    print("------------------------")
    print(
        f"Training rows  : "
        f"{len(X_train)}"
    )
    print(
        f"Validation rows: "
        f"{len(X_val)}"
    )

    model = XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
    )

    print("\nTraining Delta XGBoost...")

    model.fit(
        X_train,
        y_train,
    )

    pred_delta = model.predict(X_val)

    # -------------------------------------
    # Reconstruct prices
    # -------------------------------------
    predicted_price = (
        close_val.values
        + pred_delta
    )

    actual_price = (
        future_val.values
    )

    naive_price = (
        close_val.values
    )

    # -------------------------------------
    # Metrics
    # -------------------------------------
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

    # -------------------------------------
    # Naive baseline
    # -------------------------------------
    naive_mae = mean_absolute_error(
        actual_price,
        naive_price,
    )

    naive_rmse = np.sqrt(
        mean_squared_error(
            actual_price,
            naive_price,
        )
    )

    naive_r2 = r2_score(
        actual_price,
        naive_price,
    )

    # -------------------------------------
    # Directional Accuracy
    # -------------------------------------
    actual_direction = np.sign(
        actual_price
        - close_val.values
    )

    pred_direction = np.sign(
        predicted_price
        - close_val.values
    )

    directional_accuracy = (
        actual_direction
        == pred_direction
    ).mean() * 100

    # -------------------------------------
    # Feature Importance
    # -------------------------------------
    importance = (
        pd.DataFrame(
            {
                "Feature": X.columns,
                "Importance": model.feature_importances_,
            }
        )
        .sort_values(
            "Importance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print("\nTop Feature Importances")
    print("-----------------------")
    print(
        importance.head(20)
    )

    # -------------------------------------
    # Validation Sample
    # -------------------------------------
    results = pd.DataFrame(
        {
            "Current_Close": close_val.values,
            "Actual_Close": actual_price,
            "Predicted_Close": predicted_price,
            "Naive_Close": naive_price,
            "Actual_Delta": y_val.values,
            "Predicted_Delta": pred_delta,
        }
    )

    print("\nValidation Sample")
    print("-----------------")
    print(results.head(20))

    # -------------------------------------
    # Metrics Output
    # -------------------------------------
    print("\n==============================")
    print("Delta XGBoost Metrics")
    print("==============================")
    print(f"MAE : {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²  : {r2:.4f}")
    print(
        f"Directional Accuracy: "
        f"{directional_accuracy:.2f}%"
    )

    print("\n==============================")
    print("Naive Baseline")
    print("==============================")
    print(f"MAE : {naive_mae:.4f}")
    print(f"RMSE: {naive_rmse:.4f}")
    print(f"R²  : {naive_r2:.4f}")

    # -------------------------------------
    # Save Model Bundle
    # -------------------------------------
    bundle = {
        "model": model,
        "model_type": "delta_xgboost",
        "horizon": horizon,
        "feature_names": list(X.columns),
        "feature_importance": importance.to_dict("records"),
        "training_rows": len(X_train),
        "validation_rows": len(X_val),
        "total_rows": len(X),
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "directional_accuracy": float(
            directional_accuracy
        ),
        "naive_mae": float(
            naive_mae
        ),
        "naive_rmse": float(
            naive_rmse
        ),
        "naive_r2": float(
            naive_r2
        ),
    }

    model_out = Path(
        model_out
    )

    model_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        bundle,
        model_out,
    )

    print(
        f"\nModel saved to:\n"
        f"{model_out}"
    )

    print(
        "\nDelta XGBoost training completed successfully."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
    )

    parser.add_argument(
        "--out",
        default="models/delta_xgb_model.pkl",
    )

    parser.add_argument(
        "--horizon",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    train_delta_xgb(
        csv_path=args.csv,
        model_out=args.out,
        horizon=args.horizon,
    )