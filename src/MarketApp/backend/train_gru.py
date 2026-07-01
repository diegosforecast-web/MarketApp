import yfinance as yf
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from models.gru_model import GRUModel

# -----------------------------
# CONFIG
# -----------------------------
TICKER = "SPY"          # you can change this
LOOKBACK = 60
EPOCHS = 20
LR = 1e-3
BATCH_SIZE = 32
DEVICE = "cpu"


# -----------------------------
# DATASET CLASS
# -----------------------------
class PriceDataset(Dataset):
    def __init__(self, prices, lookback):
        self.lookback = lookback
        self.X, self.y = self.create_sequences(prices)

    def create_sequences(self, prices):
        X, y = [], []
        for i in range(len(prices) - self.lookback):
            X.append(prices[i:i+self.lookback])
            y.append(prices[i+self.lookback])
        X = np.array(X).reshape(-1, self.lookback, 1)
        y = np.array(y).reshape(-1, 1)
        return X, y

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.X[idx], dtype=torch.float32),
            torch.tensor(self.y[idx], dtype=torch.float32)
        )


# -----------------------------
# FETCH & PREPROCESS DATA
# -----------------------------
from yahooquery import Ticker

def load_data(ticker):
    t = Ticker(ticker)
    df = t.history(period="5y")

    if df is None or len(df) == 0:
        raise Exception(f"❌ No data returned for {ticker} using yahooquery.")

    df = df.reset_index()
    df = df[df["symbol"] == ticker]

    prices = df["close"].values

    mean = prices.mean()
    std = prices.std()
    norm = (prices - mean) / std

    return norm, mean, std



# -----------------------------
# TRAIN FUNCTION
# -----------------------------
def train_gru():
    print(f"📈 Loading data for {TICKER}...")
    prices, mean, std = load_data(TICKER)

    dataset = PriceDataset(prices, LOOKBACK)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    model = GRUModel().to(DEVICE)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    print("🔥 Training GRU model...")
    for epoch in range(EPOCHS):
        losses = []
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE)

            optimizer.zero_grad()
            preds = model(X_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            optimizer.step()

            losses.append(loss.item())

        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {np.mean(losses):.6f}")

    # Save model
    torch.save(model.state_dict(), "models/gru_model.pt")
    print("💾 Saved GRU model → models/gru_model.pt")


if __name__ == "__main__":
    train_gru()
