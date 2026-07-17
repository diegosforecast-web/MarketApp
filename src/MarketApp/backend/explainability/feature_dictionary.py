"""
Feature dictionary for human-readable explanations.

Purpose
-------
Translate engineered feature names into market language.

Why it matters
--------------
Users should not need to understand internal feature names to trust a forecast.
"""

from __future__ import annotations


class FeatureDictionary:
    DEFAULT_CATEGORY = "technical"
    DEFAULT_DESCRIPTION = "This feature contributed to the model prediction."

    FEATURE_METADATA = {
        "rsi_14": (
            "RSI 14",
            "momentum",
            "Measures whether recent price action is overbought or oversold.",
        ),
        "macd_percent": (
            "MACD",
            "momentum",
            "Captures changes in trend momentum.",
        ),
        "macd_hist_percent": (
            "MACD histogram",
            "momentum",
            "Measures acceleration or weakening of momentum.",
        ),
        "atr_14": (
            "ATR 14",
            "volatility",
            "Measures recent trading range and market volatility.",
        ),
        "atr_percent": (
            "ATR percent",
            "volatility",
            "Volatility normalized by price.",
        ),
        "volatility_20": (
            "20-day volatility",
            "volatility",
            "Measures recent return variability.",
        ),
        "close_vs_sma20": (
            "Price vs 20-day average",
            "trend",
            "Shows short-term trend position.",
        ),
        "close_vs_sma50": (
            "Price vs 50-day average",
            "trend",
            "Shows medium-term trend position.",
        ),
        "close_vs_sma200": (
            "Price vs 200-day average",
            "trend",
            "Shows long-term trend position.",
        ),
        "sma20_slope": (
            "20-day trend slope",
            "trend",
            "Measures short-term trend direction.",
        ),
        "sma50_slope": (
            "50-day trend slope",
            "trend",
            "Measures medium-term trend direction.",
        ),
        "sma200_slope": (
            "200-day trend slope",
            "trend",
            "Measures long-term trend direction.",
        ),
        "momentum_10": (
            "10-day momentum",
            "momentum",
            "Measures short-term price momentum.",
        ),
        "momentum_20": (
            "20-day momentum",
            "momentum",
            "Measures recent price momentum.",
        ),
        "momentum_50": (
            "50-day momentum",
            "momentum",
            "Measures intermediate price momentum.",
        ),
        "momentum_100": (
            "100-day momentum",
            "momentum",
            "Measures longer-term price momentum.",
        ),
        "volume_ratio_20": (
            "Volume ratio",
            "volume",
            "Compares recent volume with normal volume.",
        ),
        "volume_momentum_20": (
            "Volume momentum",
            "volume",
            "Measures whether volume participation is increasing.",
        ),
        "volume_volatility": (
            "Volume volatility",
            "volume",
            "Measures instability in trading activity.",
        ),
        "bb_width": (
            "Bollinger Band width",
            "volatility",
            "Measures expansion or compression in price bands.",
        ),
        "bb_position": (
            "Bollinger Band position",
            "trend",
            "Shows where price sits inside its recent range.",
        ),
        "adx_14": (
            "ADX 14",
            "trend",
            "Measures trend strength.",
        ),
        "stoch_k": (
            "Stochastic %K",
            "momentum",
            "Measures short-term price position within its range.",
        ),
        "stoch_d": (
            "Stochastic %D",
            "momentum",
            "Smooths stochastic momentum.",
        ),
        "distance_from_high": (
            "Distance from recent high",
            "risk",
            "Shows how far price is from recent resistance.",
        ),
        "distance_from_low": (
            "Distance from recent low",
            "risk",
            "Shows how far price is from recent support.",
        ),
        "trend_regime": (
            "Trend regime",
            "regime",
            "Summarizes broad trend conditions.",
        ),
        "volatility_regime": (
            "Volatility regime",
            "regime",
            "Summarizes broad volatility conditions.",
        ),
    }

    @classmethod
    def display_name(
        cls,
        feature: str,
    ) -> str:
        return cls.FEATURE_METADATA.get(
            feature,
            (
                feature,
                cls.DEFAULT_CATEGORY,
                cls.DEFAULT_DESCRIPTION,
            ),
        )[0]

    @classmethod
    def category(
        cls,
        feature: str,
    ) -> str:
        return cls.FEATURE_METADATA.get(
            feature,
            (
                feature,
                cls.DEFAULT_CATEGORY,
                cls.DEFAULT_DESCRIPTION,
            ),
        )[1]

    @classmethod
    def description(
        cls,
        feature: str,
    ) -> str:
        return cls.FEATURE_METADATA.get(
            feature,
            (
                feature,
                cls.DEFAULT_CATEGORY,
                cls.DEFAULT_DESCRIPTION,
            ),
        )[2]
