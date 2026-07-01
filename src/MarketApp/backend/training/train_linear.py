import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

from MarketApp.backend.features.engineered_features import build_14_feature_frame



def load_price_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.sort_values("date")
    df.set_index("date", inplace=True)
    return df

def build_dataset(df: pd.DataFrame, horizon: int = 1):
    feats = build_14_feature_frame(df)
    close = df["close"].loc[feats.index]
    target = close.shift(-horizon)
    dataset = feats.copy()
    dataset["target"] = target
    dataset = dataset.dropna()
    X = dataset.drop(columns=["target"]).values
    y = dataset["target"].values
    return X, y

def train_linear(csv_path: str,
                 model_out: str = "backend/models/linear_model.pkl",
                 horizon: int = 1):
    df = load_price_data(csv_path)
    X, y = build_dataset(df, horizon=horizon)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    lr = LinearRegression()
    lr.fit(X_train, y_train)

    y_pred = lr.predict(X_val)
    mse = mean_squared_error(y_val, y_pred)
    print(f"Linear validation MSE: {mse:.6f}")

    joblib.dump(
        {
            "model": lr,
            "horizon": horizon,
        },
        model_out
    )
    print(f"Saved Linear model to {model_out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", default="backend/models/linear_model.pkl")
    parser.add_argument("--horizon", type=int, default=1)
    args = parser.parse_args()

    train_linear(args.csv, model_out=args.out, horizon=args.horizon)
