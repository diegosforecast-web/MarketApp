import pandas as pd
import numpy as np


# -------------------------------------------------------
# RETURNS
# -------------------------------------------------------
def compute_returns(close: pd.Series) -> pd.DataFrame:

    return pd.DataFrame({
        "ret_1": close.pct_change(1, fill_method=None),
        "ret_2": close.pct_change(2, fill_method=None),
        "ret_3": close.pct_change(3, fill_method=None),
        "ret_5": close.pct_change(5, fill_method=None),
        "ret_10": close.pct_change(10, fill_method=None),
        "ret_20": close.pct_change(20, fill_method=None),
        "ret_50": close.pct_change(50, fill_method=None),
    })


# -------------------------------------------------------
# RSI
# -------------------------------------------------------
def compute_rsi(
    close: pd.Series,
    window: int = 14,
):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan,
    )

    return 100 - (
        100 / (1 + rs)
    )


# -------------------------------------------------------
# MACD
# -------------------------------------------------------
def compute_macd(
    close: pd.Series,
):

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False,
    ).mean()

    return macd, signal


# -------------------------------------------------------
# STOCHASTIC
# -------------------------------------------------------
def compute_stoch(
    high,
    low,
    close,
    window=14,
):

    lowest_low = (
        low.rolling(window).min()
    )

    highest_high = (
        high.rolling(window).max()
    )

    stoch_k = (
        100
        * (close - lowest_low)
        / (highest_high - lowest_low)
    )

    stoch_d = (
        stoch_k.rolling(3).mean()
    )

    return (
        stoch_k,
        stoch_d,
    )


# -------------------------------------------------------
# ATR
# -------------------------------------------------------
def compute_atr(
    high,
    low,
    close,
    window=14,
):

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return (
        tr.rolling(window)
        .mean()
    )


# -------------------------------------------------------
# ADX
# -------------------------------------------------------
def compute_adx(
    high,
    low,
    close,
    window=14,
):

    plus_dm = high.diff()

    minus_dm = (
        -low.diff()
    )

    plus_dm = plus_dm.where(
        (plus_dm > minus_dm)
        & (plus_dm > 0),
        0,
    )

    minus_dm = minus_dm.where(
        (minus_dm > plus_dm)
        & (minus_dm > 0),
        0,
    )

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = (
        tr.rolling(window)
        .mean()
    )

    plus_di = (
        100
        * plus_dm.rolling(window).mean()
        / atr
    )

    minus_di = (
        100
        * minus_dm.rolling(window).mean()
        / atr
    )

    dx = (
        (plus_di - minus_di).abs()
        /
        (plus_di + minus_di)
    ) * 100

    adx = (
        dx.rolling(window)
        .mean()
    )

    return adx


# -------------------------------------------------------
# VOLATILITY
# -------------------------------------------------------
def compute_volatility(
    close,
    window=20,
):

    return (
        close
        .pct_change(fill_method=None)
        .rolling(window)
        .std()
    )


# -------------------------------------------------------
# BOLLINGER
# -------------------------------------------------------
def compute_bollinger(
    close,
    window=20,
    num_std=2,
):

    sma = (
        close.rolling(window)
        .mean()
    )

    std = (
        close.rolling(window)
        .std()
    )

    upper = (
        sma + num_std * std
    )

    lower = (
        sma - num_std * std
    )

    return (
        sma,
        upper,
        lower,
    )


# -------------------------------------------------------
# FEATURE BUILDER
# -------------------------------------------------------
def build_14_feature_frame(
    df: pd.DataFrame,
) -> pd.DataFrame:

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    feats_ret = compute_returns(
        close
    )

    rsi_14 = compute_rsi(
        close
    )

    macd, macd_signal = (
        compute_macd(close)
    )

    macd_hist = (
        macd - macd_signal
    )

    macd_percent = (
        macd / close
    )

    macd_hist_percent = (
        macd_hist / close
    )

    stoch_k, stoch_d = (
        compute_stoch(
            high,
            low,
            close,
        )
    )

    atr_14 = compute_atr(
        high,
        low,
        close,
    )

    adx_14 = compute_adx(
        high,
        low,
        close,
    )

    volatility_20 = (
        compute_volatility(
            close
        )
    )

    # ---------------------------------------------------
    # MOVING AVERAGES
    # ---------------------------------------------------

    sma20 = (
        close.rolling(20)
        .mean()
    )

    sma50 = (
        close.rolling(50)
        .mean()
    )

    sma200 = (
        close.rolling(200)
        .mean()
    )

    close_vs_sma20 = (
        close / sma20
    ) - 1

    close_vs_sma50 = (
        close / sma50
    ) - 1

    close_vs_sma200 = (
        close / sma200
    ) - 1

    sma20_slope = (
        sma20.pct_change(5)
    )

    sma50_slope = (
        sma50.pct_change(5)
    )

    sma200_slope = (
        sma200.pct_change(20)
    )

    # ---------------------------------------------------
    # MOMENTUM
    # ---------------------------------------------------

    momentum_10 = (
        close / close.shift(10)
    ) - 1

    momentum_20 = (
        close / close.shift(20)
    ) - 1

    momentum_50 = (
        close / close.shift(50)
    ) - 1

    momentum_100 = (
        close / close.shift(100)
    ) - 1

    # ---------------------------------------------------
    # VOLATILITY
    # ---------------------------------------------------

    atr_percent = (
        atr_14 / close
    )

    volatility_regime = (
        volatility_20
        / volatility_20.rolling(50).mean()
    )

    # ---------------------------------------------------
    # VOLUME
    # ---------------------------------------------------

    volume_ma20 = (
        volume
        .rolling(20)
        .mean()
    )

    volume_ratio_20 = (
        volume / volume_ma20
    )

    volume_momentum_20 = (
        volume
        .pct_change(20)
    )

    volume_volatility = (
        volume
        .pct_change()
        .rolling(20)
        .std()
    )

    # ---------------------------------------------------
    # BOLLINGER
    # ---------------------------------------------------

    (
        bb_mid,
        bb_upper,
        bb_lower,
    ) = compute_bollinger(
        close
    )

    bb_width = (
        (bb_upper - bb_lower)
        / bb_mid
    )

    bb_position = (
        (close - bb_lower)
        /
        (bb_upper - bb_lower)
    )

    # ---------------------------------------------------
    # REGIME FEATURES
    # ---------------------------------------------------

    trend_regime = (
        sma50 > sma200
    ).astype(int)

    rolling_high_252 = (
        close.rolling(252)
        .max()
    )

    rolling_low_252 = (
        close.rolling(252)
        .min()
    )

    distance_from_high = (
        close
        / rolling_high_252
    ) - 1

    distance_from_low = (
        close
        / rolling_low_252
    ) - 1

    # ---------------------------------------------------
    # RSI LAG
    # ---------------------------------------------------

    rsi_14_lag_1 = (
        rsi_14.shift(1)
    )

    # ---------------------------------------------------
    # FINAL DATAFRAME
    # ---------------------------------------------------

    feats = pd.DataFrame({

        **feats_ret,

        "rsi_14": rsi_14,
        "rsi_14_lag_1": rsi_14_lag_1,

        "stoch_k": stoch_k,
        "stoch_d": stoch_d,

        "atr_14": atr_14,
        "atr_percent": atr_percent,

        "adx_14": adx_14,

        "volatility_20": volatility_20,
        "volatility_regime": volatility_regime,

        "macd_percent": macd_percent,
        "macd_hist_percent": macd_hist_percent,

        "close_vs_sma20": close_vs_sma20,
        "close_vs_sma50": close_vs_sma50,
        "close_vs_sma200": close_vs_sma200,

        "sma20_slope": sma20_slope,
        "sma50_slope": sma50_slope,
        "sma200_slope": sma200_slope,

        "momentum_10": momentum_10,
        "momentum_20": momentum_20,
        "momentum_50": momentum_50,
        "momentum_100": momentum_100,

        "volume_ratio_20": volume_ratio_20,
        "volume_momentum_20": volume_momentum_20,
        "volume_volatility": volume_volatility,

        "bb_width": bb_width,
        "bb_position": bb_position,

        "trend_regime": trend_regime,

        "distance_from_high": distance_from_high,
        "distance_from_low": distance_from_low,
    })

    feats["close"] = close.values
    feats["open"] = df["open"].values
    feats["high"] = high.values
    feats["low"] = low.values
    feats["volume"] = volume.values
    feats["date"] = df["date"].values

    return feats


# -------------------------------------------------------
# LATEST FEATURE VECTOR
# -------------------------------------------------------
def latest_feature_vector(
    df: pd.DataFrame,
):

    feats = build_14_feature_frame(
        df
    )

    feats = feats.dropna()

    if feats.empty:
        raise ValueError(
            "Not enough historical data."
        )

    return (
        feats
        .drop(columns=["date"])
        .iloc[-1]
    )