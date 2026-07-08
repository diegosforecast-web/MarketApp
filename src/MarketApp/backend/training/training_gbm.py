import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split

from features.engineered_features import build_14_feature_frame

# NEW
from services.model_registry import (
    ModelRegistry,
    next_model_version,
)


def load_price_data(csv_path: str) -> pd.DataFrame:
    """
    Load historical OHLCV data.
    """

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
    """
    Build training dataset.

    Target:
        Future closing price
    """

    feats = build_14_feature_frame(df)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    print(
        f"\nFeature frame shape: "
        f"{feats.shape}"
    )

    future_close = feats["close"].shift(-horizon)

    feats["target"] = np.log(
        future_close / feats["close"]
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
                "target",
            ]
        ].head(10)
    )

    X = feats.drop(
        columns=[
            "target",
            "date",
        ]
    )

    y = feats["target"]

    return X, y


def train_gbm(
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

    X, y = build_dataset(
        df,
        horizon,
    )

    print(
        f"\nUsable samples: "
        f"{len(X)}"
    )

    if len(X) < 30:
        raise ValueError(
            f"Not enough samples after feature engineering ({len(X)})."
        )

    X_train, X_val, y_train, y_val = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            shuffle=False,
        )
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

    gbm = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        random_state=42,
    )

    print("\nTraining GBM...")

    gbm.fit(
        X_train,
        y_train,
    )

    pred = gbm.predict(X_val)
# ==================================================
# GBM METRICS
# ==================================================

    current_close = X_val["close"].values

    pred_price = current_close * np.exp(pred)
    actual_price = current_close * np.exp(y_val.values)

    mae = mean_absolute_error(
        y_val.values,
        pred,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_val.values,
            pred,
        )
    )

    r2 = r2_score(
        y_val.values,
        pred,
    )

    actual_direction = np.sign(
        y_val.values
    )

    pred_direction = np.sign(
        pred
    )

    directional_accuracy = (
        actual_direction
        == pred_direction
    ).mean() * 100

# ==================================================
# NAIVE BASELINE
# ==================================================

    naive_pred = np.zeros_like(
        y_val.values
    )

    naive_mae = mean_absolute_error(
        y_val.values,
        naive_pred,
    )

    naive_rmse = np.sqrt(
        mean_squared_error(
            y_val.values,
            naive_pred,
        )
    )

    naive_r2 = r2_score(
        y_val.values,
        naive_pred,
    )

    naive_direction = np.sign(
        naive_pred
    )

    naive_directional_accuracy = (
        actual_direction
        == naive_direction
    ).mean() * 100

    print(
        f"\nDirectional Accuracy: "
        f"{directional_accuracy:.2f}%"
    )

# ==================================================
# FEATURE IMPORTANCE
# ==================================================

    importance = (
        pd.DataFrame(
            {
                "Feature": X.columns,
                "Importance":
                    gbm.feature_importances_,
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
        importance.head(15)
    )

# ==================================================
# VALIDATION SAMPLE
# ==================================================

    results = pd.DataFrame(
        {
            "Actual Return": y_val.values,
            "Predicted Return": pred,
            "Naive Return": naive_pred,
            "Actual Price": actual_price,
            "Predicted Price": pred_price,
            "Current Close": current_close,
        }
    )

    print("\nValidation Sample")
    print("-----------------")
    print(
        results.head(20)
    )

# ==================================================
# METRICS
# ==================================================

    print("\n==============================")
    print("GBM Metrics")
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
    print(
        f"Directional Accuracy: "
        f"{naive_directional_accuracy:.2f}%"
    )

# ==================================================
# SAVE MODEL
# ==================================================

    bundle = {
        "model": gbm,
        "horizon": horizon,
        "feature_names": list(
            X.columns
        ),
        "feature_importance":
            importance.to_dict(
                "records"
            ),
        "training_rows":
            len(X_train),
        "validation_rows":
            len(X_val),
        "total_rows":
            len(X),
        "mae":
            float(mae),
        "rmse":
            float(rmse),
        "r2":
            float(r2),
        "directional_accuracy":
            float(
                directional_accuracy
            ),
        "naive_mae":
            float(naive_mae),
        "naive_rmse":
            float(naive_rmse),
        "naive_r2":
            float(naive_r2),
        "naive_directional_accuracy":
            float(
                naive_directional_accuracy
            ),
    }

    registry = ModelRegistry()

    version, filename = next_model_version(
        registry.models_dir,
        "gbm_model",
    )

    model_path = (
        registry.models_dir
        / filename
    )

    model_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        bundle,
        model_path,
    )

    registry.register_model(
        task="return_forecast",
        model_type="gbm",
        file=filename,
        version=version,
        metrics={
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2),
            "directional_accuracy": float(
                directional_accuracy
            ),
        },
        parameters={
            "horizon": horizon,
            "training_rows": len(X_train),
            "validation_rows": len(X_val),
        },
        feature_names=list(
            X.columns
        ),
        make_production=True,
        notes="Automatically registered by training_gbm.",
    )

    print(
        f"\nModel version {version} saved:"
    )

    print(model_path)

    print(
        "\nRegistry updated successfully."
    )

    print(
        "\nGBM training completed successfully."
    )

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
        help="Historical price CSV",
    )

    parser.add_argument(
        "--out",
        default="models/gbm_model.pkl",
        help=(
            "Legacy output argument. "
            "Models are automatically versioned "
            "through the Model Registry."
        ),
    )

    parser.add_argument(
        "--horizon",
        type=int,
        default=1,
        help="Prediction horizon in trading days",
    )

    args = parser.parse_args()

    train_gbm(
        csv_path=args.csv,
        model_out=args.out,
        horizon=args.horizon,
    )