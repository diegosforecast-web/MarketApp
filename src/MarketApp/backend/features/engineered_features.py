import pandas as pd
import numpy as np

# -----------------------------
# BASIC RETURN FEATURES
# -----------------------------
def compute_returns(close: pd.Series) -> pd.DataFrame:
    ret = close.pct_change(fill_method=None)

    feats = pd.DataFrame({
        "ret_1": ret,
        "ret_2": close.pct_change(2, fill_method=None),
        "ret_3": close.pct_change(3, fill_method=None),
        "ret_5": close.pct_change(5, fill_method=None),
        "ret_10": close.pct_change(10, fill_method=None),
        "ret_20": close.pct_change(20, fill_method=None),
        "ret_50": close.pct_change(50, fill_method=None),
    })

    return feats


# -----------------------------
# RSI
# -----------------------------
def compute_rsi(close: pd.Series, window=14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


# -----------------------------
# MACD
# -----------------------------
def compute_macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


# -----------------------------
# STOCHASTIC OSCILLATOR
# -----------------------------
def compute_stoch(high, low, close, window=14):
    lowest_low = low.rolling(window).min()
    highest_high = high.rolling(window).max()
    stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    stoch_d = stoch_k.rolling(3).mean()
    return stoch_k, stoch_d


# -----------------------------
# ATR
# -----------------------------
def compute_atr(high, low, close, window=14):
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(window).mean()
    return atr


# -----------------------------
# VOLATILITY
# -----------------------------
def compute_volatility(close, window=20):
    return close.pct_change(fill_method=None).rolling(window).std()


# -----------------------------
# MAIN FEATURE BUILDER
# -----------------------------
def build_14_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Core engineered features
    feats_ret = compute_returns(close)
    rsi_14 = compute_rsi(close)
    macd, macd_signal = compute_macd(close)
    stoch_k, stoch_d = compute_stoch(high, low, close)
    atr_14 = compute_atr(high, low, close)
    vol_20 = compute_volatility(close)

    # Build final feature frame
    feats = pd.DataFrame({
        "ret_1": feats_ret["ret_1"],
        "ret_2": feats_ret["ret_2"],
        "ret_3": feats_ret["ret_3"],
        "ret_5": feats_ret["ret_5"],
        "ret_10": feats_ret["ret_10"],
        "ret_20": feats_ret["ret_20"],
        "ret_50": feats_ret["ret_50"],
        "rsi_14": rsi_14,
        "macd": macd,
        "macd_signal": macd_signal,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "atr_14": atr_14,
        "volatility_20": vol_20,
    })

    # -----------------------------
    # CRITICAL FIX: INCLUDE OHLCV
    # -----------------------------
    feats["close"] = df["close"].values
    feats["open"] = df["open"].values
    feats["high"] = df["high"].values
    feats["low"] = df["low"].values
    feats["volume"] = df["volume"].values
    feats["date"] = df["date"].values

    return feats
