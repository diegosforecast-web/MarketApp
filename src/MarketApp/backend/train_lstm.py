import yfinance as yf
import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler

# -----------------------------
# CONFIG
# -----------------------------
TICKER = "AAPL"          # change if you want
YEARS = 3                # 3 years of history
WINDOW_SIZE = 60         # past days used to predict next day
EPOCHS = 20              # adjust if you want more training
BATCH_SIZE = 32
MODEL_PATH = "lstm.h5"


def load_data(ticker: str, years: int):
    period_str = f"{years}y"
    df = yf.download(ticker, period=period_str, interval="1d")
    if df.empty:
        raise ValueError("No data downloaded")
    closes = df["Close"].values.reshape(-1, 1)
    return closes


def create_sequences(data, window_size):
    X = []
    y = []
    for i in range(len(data) - window_size):
        X.append(data[i:i + window_size])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)


def main():
    print(f"Downloading {YEARS} years of data for {TICKER}...")
    closes = load_data(TICKER, YEARS)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(closes)

    X, y = create_sequences(scaled, WINDOW_SIZE)
    print(f"Created {X.shape[0]} sequences.")

    model = Sequential()
    model.add(LSTM(64, input_shape=(WINDOW_SIZE, 1)))
    model.add(Dense(1))

    model.compile(optimizer=Adam(learning_rate=0.001), loss="mse")

    print("Training LSTM...")
    model.fit(X, y, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=1)

    print(f"Saving model to {MODEL_PATH}...")
    model.save(MODEL_PATH)

    # Save scaler for later use
    scaler_df = pd.DataFrame({
        "min": scaler.data_min_,
        "max": scaler.data_max_
    })
    scaler_df.to_csv("lstm_scaler.csv", index=False)

    print("Done.")


if __name__ == "__main__":
    main()
