import argparse
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
import joblib

from MarketApp.backend.features.engineered_features import build_14_feature_frame


def load_price_data(csv_path: str) -> pd.DataFrame:
    """
    Load OHLCV CSV and ensure correct types.
    """
    df = pd.read_csv(csv_path)

    # Fix column types
    df["date"] = pd.to_datetime(df["date"])

    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df


def build_dataset(df: pd.DataFrame, horizon: int):
    """
    Build feature matrix X and target y using engineered features.
    """
    feats = build_14_feature_frame(df)

    # Drop rows with NaNs from rolling windows
    feats = feats.dropna().reset_index(drop=True)

    # Target: future close price horizon days ahead
    feats["target"] = feats["close"].shift(-horizon)

    feats = feats.dropna().reset_index(drop=True)

    X = feats.drop(columns=["target", "date"])
    y = feats["target"]

    return X, y


def train_gbm(csv_path: str, model_out: str, horizon: int):
    """
    Train a Gradient Boosting model using engineered features.
    """
    print(f"Loading data from: {csv_path}")
    df = load_price_data(csv_path)

    print("Building dataset...")
    X, y = build_dataset(df, horizon=horizon)

    print(f"Dataset size: {len(X)} rows")

    if len(X) < 30:
        raise ValueError(
            f"Not enough data after feature engineering. Need at least 30 rows, got {len(X)}."
        )

    print("Splitting train/validation...")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    print("Training GBM model...")
    gbm = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        random_state=42,
    )

    gbm.fit(X_train, y_train)

    val_score = gbm.score(X_val, y_val)
    print(f"Validation R^2: {val_score:.4f}")

    print(f"Saving model to: {model_out}")
    joblib.dump(gbm, model_out)

    print("GBM training complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, required=True)
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--horizon", type=int, default=1)

    args = parser.parse_args()

    train_gbm(args.csv, model_out=args.out, horizon=args.horizon)
