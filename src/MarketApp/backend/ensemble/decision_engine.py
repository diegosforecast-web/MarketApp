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
        if not 0.50 < buy_probability_threshold < 1.0:
            raise ValueError(
                "buy_probability_threshold must be between 0.50 and 1.00."
            )

        if min_expected_return <= 0:
            raise ValueError(
                "min_expected_return must be greater than zero."
            )

        if not buy_probability_threshold <= high_confidence_threshold <= 1.0:
            raise ValueError(
                "high_confidence_threshold must be greater than or equal "
                "to the buy threshold and no greater than 1.00."
            )

        self.buy_probability_threshold = buy_probability_threshold
        self.sell_probability_threshold = (
            1.0 - buy_probability_threshold
        )
        self.min_expected_return = min_expected_return
        self.high_confidence_threshold = high_confidence_threshold

        self.registry = ModelRegistry()
        self._models: dict[int, tuple[object, object]] = {}

    def supported_horizons(self) -> list[int]:
        return self.registry.supported_horizons()

    def _load_models(self, horizon: int):
        if horizon not in self._models:
            self._models[horizon] = (
                self.registry.load_horizon_predictor(
                    "direction",
                    horizon,
                ),
                self.registry.load_horizon_predictor(
                    "return_forecast",
                    horizon,
                ),
            )

        return self._models[horizon]

    def signal_probability(
        self,
        direction_probability: float,
        recommendation: str,
    ) -> float:
        """
        Return confidence in the displayed directional signal.

        direction_probability is the calibrated probability of an upward
        threshold move. SELL therefore uses the complementary probability.
        HOLD reports the stronger directional class while making no trade call.
        """
        probability = min(
            1.0,
            max(0.0, float(direction_probability)),
        )

        recommendation = str(recommendation).upper()

        if recommendation == "SELL":
            return 1.0 - probability

        if recommendation == "BUY":
            return probability

        # HOLD means the models did not jointly support a trade.
        # Keep its displayed confidence conservative.
        return min(
            max(probability, 1.0 - probability),
            self.buy_probability_threshold,
        )

    def _confidence_level(
        self,
        signal_probability: float,
    ) -> str:
        if signal_probability >= self.high_confidence_threshold:
            return "HIGH"

        if signal_probability >= self.buy_probability_threshold:
            return "MEDIUM"

        return "LOW"

    def predict_point(
        self,
        ticker: str,
        price_df: pd.DataFrame,
        horizon: int,
    ) -> EnsembleDecision:
        horizon = int(horizon)
        supported = self.supported_horizons()

        if horizon not in supported:
            raise ValueError(
                f"Unsupported forecast horizon: {horizon}. "
                f"Available production horizons: {supported}"
            )

        direction_model, return_model = self._load_models(horizon)

        return self.decide(
            ticker=ticker,
            direction_probability=direction_model.predict_proba(
                price_df
            ),
            expected_return=return_model.predict_expected_return(
                price_df
            ),
        )

    def predict(
        self,
        ticker: str,
        price_df: pd.DataFrame,
        horizon: int,
    ) -> EnsembleDecision:
        horizon = int(horizon)

        decision = self.predict_point(
            ticker=ticker,
            price_df=price_df,
            horizon=horizon,
        )

        direction_model, _ = self._load_models(horizon)

        explanation_confidence = self.signal_probability(
            decision.direction_probability,
            decision.recommendation,
        )

        explanation = direction_model.explain(
            price_df=price_df,
            prediction=decision.recommendation,
            confidence=explanation_confidence,
        )

        return EnsembleDecision(
            ticker=decision.ticker,
            direction_probability=decision.direction_probability,
            expected_return=decision.expected_return,
            recommendation=decision.recommendation,
            confidence=decision.confidence,
            reasons=decision.reasons,
            warnings=decision.warnings,
            explanation=explanation.to_dict(),
            historical_confidence=self._historical_confidence(
                horizon
            ),
        )

    def decide(
        self,
        ticker: str,
        direction_probability: float,
        expected_return: float,
    ) -> EnsembleDecision:
        direction_probability = min(
            1.0,
            max(0.0, float(direction_probability)),
        )
        expected_return = float(expected_return)

        buy_signal = (
            direction_probability
            >= self.buy_probability_threshold
            and expected_return
            >= self.min_expected_return
        )

        sell_signal = (
            direction_probability
            <= self.sell_probability_threshold
            and expected_return
            <= -self.min_expected_return
        )

        if buy_signal:
            recommendation = "BUY"
        elif sell_signal:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        signal_probability = self.signal_probability(
            direction_probability,
            recommendation,
        )
        confidence = self._confidence_level(
            signal_probability
        )

        reasons: list[str] = []
        warnings: list[str] = []

        if recommendation == "BUY":
            reasons.extend(
                [
                    (
                        "The direction model supports an upward move "
                        "above the buy threshold."
                    ),
                    (
                        "The return model forecasts enough upside to "
                        "support a BUY signal."
                    ),
                ]
            )

        elif recommendation == "SELL":
            reasons.extend(
                [
                    (
                        "The direction model supports a downward move "
                        "above the sell-confidence threshold."
                    ),
                    (
                        "The return model forecasts enough downside to "
                        "support a SELL signal."
                    ),
                ]
            )

        else:
            if (
                self.sell_probability_threshold
                < direction_probability
                < self.buy_probability_threshold
            ):
                warnings.append(
                    "Directional evidence is mixed and does not meet "
                    "the BUY or SELL threshold."
                )
            elif (
                direction_probability
                >= self.buy_probability_threshold
            ):
                reasons.append(
                    "The direction model leans upward."
                )
                warnings.append(
                    "The return forecast does not show enough upside "
                    "to justify a BUY signal."
                )
            else:
                reasons.append(
                    "The direction model leans downward."
                )
                warnings.append(
                    "The return forecast does not show enough downside "
                    "to justify a SELL signal."
                )

            if (
                direction_probability
                >= self.buy_probability_threshold
                and expected_return < 0
            ):
                warnings.append(
                    "The direction and return models disagree."
                )

            if (
                direction_probability
                <= self.sell_probability_threshold
                and expected_return > 0
            ):
                warnings.append(
                    "The direction and return models disagree."
                )

        return EnsembleDecision(
            ticker=ticker,
            direction_probability=direction_probability,
            expected_return=expected_return,
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
        )

    def _historical_confidence(
        self,
        horizon: int,
    ) -> dict:
        info = self.registry.get_horizon_model_info(
            "direction",
            horizon,
        )
        metrics = info.get("metrics", {})
        parameters = info.get("parameters", {})

        return {
            "source": "production_direction_model_validation",
            "model_version": info.get("version"),
            "git_commit": info.get("git_commit"),
            "horizon": horizon,
            "accuracy": metrics.get("accuracy"),
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1": metrics.get("f1"),
            "auc": metrics.get("auc"),
            "calibration_method": parameters.get(
                "calibration_method"
            ),
            "validation_rows": parameters.get(
                "validation_rows"
            ),
        }
