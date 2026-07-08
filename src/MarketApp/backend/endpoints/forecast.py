from fastapi import APIRouter

from schemas.prediction import PredictionRequest
from services.prediction_service import PredictionService

router = APIRouter()

prediction_service = PredictionService()


@router.get("/")
async def get_forecast(
    ticker: str,
    horizon: int = 5,
):
    """
    Forecast endpoint.

    This endpoint delegates all business logic to PredictionService.
    """

    request = PredictionRequest(
        ticker=ticker,
        horizon=horizon,
    )

    return await prediction_service.predict(request)