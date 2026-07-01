import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
import os
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------
# 1. Load price history (same loader your backend uses)
# ---------------------------------------------------------

from core.data_loader import load_price_history


def build_features(prices, window=12):
    """
    Build 12-feature regime dataset.
    Features:
        - 12 lagged returns (pct change)
    Label:
        - bullish / bearish / neutral based on last return
    """

    returns = pd.Series(prices).pct_change().dropna().values

    X = []
    y = []

    for i in range(window, len(returns)):
        window_slice = returns[i - window:i]

        # Features = last 12 returns
        X.append(window_slice)

        # Label based on next-day return
        next_ret = returns[i]

        if next_ret > 0.002:
            y.append("bullish")
        elif next_ret < -0.002:
            y.append("bearish")
        else:
            y.append("neutral")

    return np.array(X), np.array(y)


def train_regime_model(ticker="SPY"):
    print(f"Loading price history for {ticker}...")
    prices = load_price_history(ticker)

    print("Building features...")
    X, y = build_features(prices, window=12)

    print(f"Dataset size: {X.shape}, labels: {set(y)}")

    # ---------------------------------------------------------
    # 2. Scale features
    # ---------------------------------------------------------

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Save scaler
    scaler_path = os.path.join(os.path.dirname(__file__), "regime_scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"Saved scaler → {scaler_path}")

    # ---------------------------------------------------------
    # 3. Train LightGBM classifier
    # ---------------------------------------------------------

    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=-1,
        num_leaves=31,
        objective="multiclass",
        random_state=42,
    )

    print("Training LightGBM regime model...")
    model.fit(X_scaled, y)

    # ---------------------------------------------------------
    # 4. Save model
    # ---------------------------------------------------------

    model_path = os.path.join(os.path.dirname(__file__), "regime_model.pkl")
    joblib.dump(model, model_path)
    print(f"Saved model → {model_path}")

    print("Training complete.")


if __name__ == "__main__":
    train_regime_model("SPY")
