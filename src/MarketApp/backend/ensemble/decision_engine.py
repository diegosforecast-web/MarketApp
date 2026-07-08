"""
Ensemble Decision Engine for DiMarket.

Purpose
-------
Combine production model outputs into one clear decision.

This first production-connected version loads both production models from the
Model Registry:
- direction -> DirectionForecaster
- return_forecast -> GBMForecaster
"""

from __future__ import annotations

import pandas as pd

from ensemble.models import EnsembleDecision
from services.model_registry import ModelRegistry


class EnsembleDecisionEngine:
    def __init__(
        self,
        buy_probability_threshold: float = 0.60,
        min_expected_return: float = 0.005,
        high_confidence_threshold: float = 0.70,
    ) -> None:
        self.buy_probability_threshold = buy_probability_threshold
        self.min_expected_return = min_expected_return
        self.high_confidence_threshold = high_confidence_threshold

        registry = ModelRegistry()

        self.direction_model = registry.load_predictor(
            "direction"
        )

        self.return_model = registry.load_predictor(
            "return_forecast"
        )

    def predict(
        self,
        ticker: str,
        price_df: pd.DataFrame,
    ) -> EnsembleDecision:
        direction_probability = self.direction_model.predict_proba(
            price_df
        )

        expected_return = self.return_model.predict_expected_return(
            price_df
        )

        return self.decide(
            ticker=ticker,
            direction_probability=direction_probability,
            expected_return=expected_return,
        )

    def decide(
        self,
        ticker: str,
        direction_probability: float,
        expected_return: float,
    ) -> EnsembleDecision:
        reasons: list[str] = []
        warnings: list[str] = []

        if direction_probability >= self.high_confidence_threshold:
            confidence = "HIGH"
        elif direction_probability >= self.buy_probability_threshold:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        if direction_probability >= self.buy_probability_threshold:
            reasons.append(
                "Direction model probability is above the buy threshold."
            )
        else:
            warnings.append(
                "Direction model probability is below the buy threshold."
            )

        if expected_return >= self.min_expected_return:
            reasons.append(
                "Return forecast is positive enough to support the signal."
            )
        else:
            warnings.append(
                "Return forecast does not provide enough upside."
            )

        if (
            direction_probability >= self.buy_probability_threshold
            and expected_return >= self.min_expected_return
        ):
            recommendation = "BUY"
        elif direction_probability >= self.buy_probability_threshold:
            recommendation = "HOLD"
        else:
            recommendation = "REJECT"

        return EnsembleDecision(
            ticker=ticker,
            direction_probability=float(direction_probability),
            expected_return=float(expected_return),
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
        )