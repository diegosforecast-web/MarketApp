from services.market_data_service import MarketDataService
from services.model_registry import ModelRegistry

from schemas.prediction import PredictionRequest
from schemas.response import PredictionResponse


class PredictionService:
    """
    Executes the end-to-end prediction workflow.
    """

    def __init__(self):
        self.market_data = MarketDataService()
        self.registry = ModelRegistry()

    async def predict(
        self,
        request: PredictionRequest,
    ) -> PredictionResponse:

        # Load market history
        history = self.market_data.get_history(request.ticker)

        if history.empty:
            raise RuntimeError("No market data returned.")

        current_price = float(history["close"].iloc[-1])

        predictor = self.registry.get_predictor()

        print(history.columns.tolist())
        print(history.head())

        forecast_price = float(predictor.predict(history))

        expected_move = (
            (forecast_price - current_price)
            / current_price
            * 100
        )

        confidence = min(
            95,
            max(
                50,
                int(90 - abs(expected_move)),
            ),
        )

        if confidence >= 85:
            level = "High"
        elif confidence >= 70:
            level = "Medium"
        else:
            level = "Low"

        return PredictionResponse(
            ticker=request.ticker.upper(),
            current_price=round(current_price, 2),
            forecast_price=round(forecast_price, 2),
            expected_move_pct=round(expected_move, 2),
            confidence=confidence,
            confidence_level=level,
            horizon=request.horizon,
            model="GBM",
            details_available=True,
        )