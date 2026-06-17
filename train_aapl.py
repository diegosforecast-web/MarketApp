import yfinance as yf
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping

TICKER = "AAPL"
LOOKBACK = 60

print(f"Training model for {TICKER}...")

df = yf.download(TICKER, period="5y", interval="1d")
prices = df["Close"].dropna().values.reshape(-1, 1)

scaler = MinMaxScaler()
scaled = scaler.fit_transform(prices)

X, y = [], []
for i in range(LOOKBACK, len(scaled)):
    X.append(scaled[i-LOOKBACK:i])
    y.append(scaled[i])

X, y = np.array(X), np.array(y)

model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(LOOKBACK, 1)),
    LSTM(32),
    Dense(1)
])

model.compile(optimizer="adam", loss="mse")

model.fit(
    X, y,
    epochs=50,
    batch_size=32,
    validation_split=0.1,
    callbacks=[EarlyStopping(patience=5, restore_best_weights=True)]
)

model.save("models/aapl_lstm.h5")
print("Saved: models/aapl_lstm.h5")
