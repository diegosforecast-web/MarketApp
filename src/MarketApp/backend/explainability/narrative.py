"""
Narrative builder for model explanations.

Purpose
-------
Turn feature contributions into concise, plain-language explanations.

Why it matters
--------------
Trust improves when users understand the evidence supporting a forecast,
the main source of uncertainty, and what the confidence estimate represents.
"""

from __future__ import annotations

from explainability.models import FeatureContribution


class NarrativeBuilder:
    @staticmethod
    def _confidence_label(confidence: float) -> str:
        percentage = confidence * 100

        if confidence >= 0.70:
            return (
                f"Confidence is relatively high at {percentage:.0f}%, "
                "meaning the calibrated direction model currently sees "
                "stronger-than-usual evidence for this outcome."
            )

        if confidence >= 0.60:
            return (
                f"Confidence is moderate at {percentage:.0f}%. "
                "The model sees enough evidence to support the signal, "
                "but meaningful uncertainty remains."
            )

        return (
            f"Confidence is limited at {percentage:.0f}%. "
            "The available evidence is not strong enough to support a "
            "high-conviction directional signal."
        )

    @staticmethod
    def build_summary(
        prediction: str,
        confidence: float,
        positive_features: list[FeatureContribution],
        negative_features: list[FeatureContribution],
    ) -> str:
        prediction_label = str(prediction or "forecast").upper()
        parts = [
            f"DiMarket produced a {prediction_label} decision from the "
            "current market evidence."
        ]

        if prediction_label == "SELL":
            supportive_features = negative_features
            opposing_features = positive_features
        else:
            supportive_features = positive_features
            opposing_features = negative_features

        if supportive_features:
            strongest = supportive_features[0]
            parts.append(
                f"The strongest supporting factor is "
                f"{strongest.display_name}: {strongest.description}"
            )
        else:
            parts.append(
                "The model did not identify one dominant supporting factor."
            )

        if opposing_features:
            strongest_risk = opposing_features[0]
            parts.append(
                f"The main opposing factor is "
                f"{strongest_risk.display_name}: "
                f"{strongest_risk.description}"
            )
        else:
            parts.append(
                "No dominant opposing feature was identified in this "
                "observation."
            )

        parts.append(
            NarrativeBuilder._confidence_label(
                float(confidence),
            )
        )

        parts.append(
            "This explanation reflects the latest available market data. "
            "It may change as price, volume, volatility, and trend "
            "conditions evolve."
        )

        return " ".join(parts)

    @staticmethod
    def direction_label(
        impact: float,
    ) -> str:
        if impact > 0:
            return "supportive"

        if impact < 0:
            return "opposing"

        return "neutral"
