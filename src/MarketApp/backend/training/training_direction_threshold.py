import argparse
from pathlib import Path

import joblib
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from sklearn.model_selection import train_test_split

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

    df[numeric_cols] = (
        df[numeric_cols]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
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
    threshold: float,
):

    feats = build_14_feature_frame(df)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    feats["future_close"] = (
        feats["close"]
        .shift(-horizon)
    )

    feats["future_return"] = (
        feats["future_close"]
        / feats["close"]
    ) - 1

    buy_mask = (
        feats["future_return"]
        > threshold
    )

    sell_mask = (
        feats["future_return"]
        < -threshold
    )

    feats = feats[
        buy_mask | sell_mask
    ].copy()

    feats["target"] = (
        feats["future_return"]
        > threshold
    ).astype(int)

    feats = (
        feats.dropna()
        .reset_index(drop=True)
    )

    print(
        f"\nThreshold: {threshold:.2%}"
    )

    print(
        f"Remaining Samples: {len(feats)}"
    )

    print(
        "\nClass Distribution"
    )

    print(
        feats["target"]
        .value_counts()
    )

    X = feats.drop(
        columns=[
            "target",
            "future_close",
            "future_return",
            "date",

            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    y = feats["target"]

    return X, y


# ==========================================================
# TRAINING
# ==========================================================
def train_direction_threshold(
    csv_path: str,
    model_out: str,
    horizon: int,
    threshold: float,
):

    print(
        f"\nLoading data from: {csv_path}"
    )

    df = load_price_data(
        csv_path
    )

    print(
        "\nBuilding threshold dataset..."
    )

    X, y = build_dataset(
        df,
        horizon,
        threshold,
    )

    (
        X_train,
        X_val,
        y_train,
        y_val,
    ) = train_test_split(
        X,
        y,
        test_size=0.20,
        shuffle=False,
    )

    print(
        f"\nTraining Rows: {len(X_train)}"
    )

    print(
        f"Validation Rows: {len(X_val)}"
    )

    positives = (
        y_train == 1
    ).sum()

    negatives = (
        y_train == 0
    ).sum()

    scale_pos_weight = (
        negatives / positives
    )

    print(
        f"\nScale Pos Weight: {scale_pos_weight:.4f}"
    )

    majority_baseline = max(
        y_val.mean(),
        1 - y_val.mean(),
    )

    print(
        f"Majority Baseline Accuracy: "
        f"{majority_baseline:.4f}"
    )

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

    print(
        "\nTraining Threshold Direction XGBoost..."
    )

    model.fit(
        X_train,
        y_train,
    )

    probabilities = (
        model.predict_proba(X_val)
        [:, 1]
    )

    pred = (
        probabilities >= 0.50
    ).astype(int)

    accuracy = accuracy_score(
        y_val,
        pred,
    )

    precision = precision_score(
        y_val,
        pred,
        zero_division=0,
    )

    recall = recall_score(
        y_val,
        pred,
        zero_division=0,
    )

    f1 = f1_score(
        y_val,
        pred,
        zero_division=0,
    )

    auc = roc_auc_score(
        y_val,
        probabilities,
    )

    print("\n==============================")
    print("THRESHOLD DIRECTION METRICS")
    print("==============================")

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

    print(
        f"AUC      : {auc:.4f}"
    )

    ranking = pd.DataFrame({
        "probability": probabilities,
        "actual": y_val.values,
    })

    ranking = (
        ranking
        .sort_values(
            "probability",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    top10 = (
        ranking.head(10)
        ["actual"]
        .mean()
    )

    top20 = (
        ranking.head(20)
        ["actual"]
        .mean()
    )

    top30 = (
        ranking.head(30)
        ["actual"]
        .mean()
    )

    print("\n==============================")
    print("PROBABILITY RANKING")
    print("==============================")

    print(
        f"Top10 Win Rate: {top10:.4f}"
    )

    print(
        f"Top20 Win Rate: {top20:.4f}"
    )

    print(
        f"Top30 Win Rate: {top30:.4f}"
    )

    importance = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_,
    })

    importance = (
        importance
        .sort_values(
            "importance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print("\n==============================")
    print("TOP 25 FEATURES")
    print("==============================")

    print(
        importance.head(25)
    )

    bundle = {
        "model": model,
        "model_type":
            "direction_threshold_xgb",
        "horizon": horizon,
        "threshold": threshold,
        "feature_names":
            list(X.columns),
        "feature_importance":
            importance.to_dict(
                orient="records"
            ),
        "accuracy":
            float(accuracy),
        "precision":
            float(precision),
        "recall":
            float(recall),
        "f1":
            float(f1),
        "auc":
            float(auc),
        "top10":
            float(top10),
        "top20":
            float(top20),
        "top30":
            float(top30),
        "training_rows":
            len(X_train),
        "validation_rows":
            len(X_val),
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
        f"\nModel saved to:\n{model_out}"
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
        "--out",
        default=(
            "models/"
            "direction_threshold_xgb.pkl"
        ),
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

    args = parser.parse_args()

    train_direction_threshold(
        csv_path=args.csv,
        model_out=args.out,
        horizon=args.horizon,
        threshold=args.threshold,
    )