from ensemble.decision_engine import EnsembleDecisionEngine
from services.market_data_service import MarketDataService

from schemas.prediction import PredictionRequest
from schemas.response import PredictionResponse


class PredictionService:
    """
    Executes the end-to-end prediction workflow.
    """

    def __init__(self):
        self.market_data = MarketDataService()
        self.ensemble = EnsembleDecisionEngine()

    async def predict(
        self,
        request: PredictionRequest,
    ) -> PredictionResponse:

        history = self.market_data.get_history(
            request.ticker
        )

        if history.empty:
            raise RuntimeError(
                "No market data returned."
            )

        current_price = float(
            history["close"].iloc[-1]
        )

        decision = self.ensemble.predict(
            ticker=request.ticker.upper(),
            price_df=history,
        )

        expected_move_pct = (
            decision.expected_return
            * 100
        )

        forecast_price = (
            current_price
            * (1 + decision.expected_return)
        )

        confidence = int(
            round(
                decision.direction_probability
                * 100
            )
        )

        return PredictionResponse(
            ticker=request.ticker.upper(),
            current_price=round(current_price, 2),
            forecast_price=round(forecast_price, 2),
            expected_move_pct=round(expected_move_pct, 2),
            confidence=confidence,
            confidence_level=decision.confidence,
            horizon=request.horizon,
            recommendation=decision.recommendation,
            model="EnsembleDecisionEngine",
            details_available=True,
            reasons=decision.reasons,
            warnings=decision.warnings,
            explanation=decision.explanation,
            historical_confidence=decision.historical_confidence,
        )