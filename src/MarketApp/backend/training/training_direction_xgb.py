import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from sklearn.model_selection import train_test_split

from xgboost import XGBClassifier

from features.engineered_features import (
    build_14_feature_frame,
)


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

    print("\n==============================")
    print("Dataset Preview")
    print("==============================")
    print(df.head())

    print("\nColumns:")
    print(df.columns.tolist())

    print(f"\nDataset Shape: {df.shape}")

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
        f"\nFeature frame shape: {feats.shape}"
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

    print("\nTarget Alignment Preview")
    print("------------------------")

    preview = feats[
        [
            "date",
            "close",
            "future_close",
            "target",
        ]
    ].head(10)

    print(preview)

    X = feats.drop(
        columns=[
            "target",
            "future_close",
            "date",
        ]
    )

    y = feats["target"]

    return X, y


def train_direction_xgb(
    csv_path: str,
    model_out: str,
    horizon: int,
):
    print(
        f"\nLoading data from: {csv_path}"
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
        f"\nUsable samples: {len(X)}"
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
        f"Training rows  : {len(X_train)}"
    )
    print(
        f"Validation rows: {len(X_val)}"
    )

    model = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
    )

    print(
        "\nTraining Directional XGBoost..."
    )

    model.fit(
        X_train,
        y_train,
    )

    pred = model.predict(X_val)

    accuracy = accuracy_score(
        y_val,
        pred,
    )

    print(
        f"\nDirectional Accuracy: {accuracy * 100:.2f}%"
    )

    importance = (
        pd.DataFrame(
            {
                "Feature": X.columns,
                "Importance": (
                    model.feature_importances_
                ),
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

    print("\nConfusion Matrix")
    print("----------------")
    print(
        confusion_matrix(
            y_val,
            pred,
        )
    )

    print("\nClassification Report")
    print("---------------------")
    print(
        classification_report(
            y_val,
            pred,
            digits=4,
        )
    )

    bundle = {
        "model": model,
        "horizon": horizon,
        "feature_names": list(X.columns),
        "feature_importance": (
            importance.to_dict("records")
        ),
        "accuracy": float(accuracy),
    }

    model_out = Path(model_out)

    model_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        bundle,
        model_out,
    )

    print(
        f"\nModel saved to:\n{model_out}"
    )

    print(
        "\nDirectional XGBoost training completed successfully."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
    )

    parser.add_argument(
        "--out",
        default="models/direction_xgb_model.pkl",
    )

    parser.add_argument(
        "--horizon",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    train_direction_xgb(
        csv_path=args.csv,
        model_out=args.out,
        horizon=args.horizon,
    )