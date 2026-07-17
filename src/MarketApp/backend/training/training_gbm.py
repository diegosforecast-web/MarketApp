import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from features.engineered_features import build_14_feature_frame
from services.model_registry import ModelRegistry, next_model_version


def load_price_data(csv_path: str) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path)
    df.columns = df.columns.str.lower()
    df["date"] = pd.to_datetime(df["date"])

    numeric = ["open", "high", "low", "close", "volume"]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def build_dataset(df: pd.DataFrame, horizon: int):
    feats = build_14_feature_frame(df).dropna().reset_index(drop=True)
    future_close = feats["close"].shift(-horizon)
    feats["target"] = np.log(future_close / feats["close"])
    feats = feats.dropna().reset_index(drop=True)

    X = feats.drop(columns=["target", "date"])
    y = feats["target"]
    return X, y


def train_gbm(csv_path: str, model_out: str, horizon: int):
    print(f"\nTraining {horizon}-day GBM return model")
    df = load_price_data(csv_path)
    X, y = build_dataset(df, horizon)

    if len(X) < 30:
        raise ValueError(f"Not enough samples ({len(X)}).")

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, shuffle=False
    )

    model = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        random_state=42,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_val)

    mae = mean_absolute_error(y_val.values, pred)
    rmse = np.sqrt(mean_squared_error(y_val.values, pred))
    r2 = r2_score(y_val.values, pred)
    directional_accuracy = (
        np.sign(y_val.values) == np.sign(pred)
    ).mean() * 100

    importance = (
        pd.DataFrame(
            {
                "Feature": X.columns,
                "Importance": model.feature_importances_,
            }
        )
        .sort_values("Importance", ascending=False)
        .reset_index(drop=True)
    )

    bundle = {
        "model": model,
        "horizon": horizon,
        "feature_names": list(X.columns),
        "feature_importance": importance.to_dict("records"),
        "training_rows": len(X_train),
        "validation_rows": len(X_val),
        "total_rows": len(X),
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "directional_accuracy": float(directional_accuracy),
    }

    registry = ModelRegistry()
    prefix = f"gbm_return_h{horizon}"
    version, filename = next_model_version(registry.models_dir, prefix)
    model_path = registry.models_dir / filename
    joblib.dump(bundle, model_path)

    task = registry.task_for_horizon("return_forecast", horizon)
    registry.register_model(
        task=task,
        model_type="gbm",
        file=filename,
        version=version,
        metrics={
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2),
            "directional_accuracy": float(directional_accuracy),
        },
        parameters={
            "horizon": horizon,
            "training_rows": len(X_train),
            "validation_rows": len(X_val),
        },
        feature_names=list(X.columns),
        make_production=False,
        notes=f"Horizon-aware GBM return model ({horizon} days).",
    )

    print(f"Registered {task} version {version}: {model_path}")
    print(
        f"MAE={mae:.4f}, RMSE={rmse:.4f}, R2={r2:.4f}, "
        f"Directional Accuracy={directional_accuracy:.2f}%"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/price_history.csv")
    parser.add_argument("--out", default="models/gbm_model.pkl")
    parser.add_argument("--horizon", type=int, default=1)
    args = parser.parse_args()

    train_gbm(args.csv, args.out, args.horizon)
