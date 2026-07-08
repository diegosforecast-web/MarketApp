from pydantic import BaseModel


class PredictionResponse(BaseModel):
    """
    Standard response returned to the frontend.
    """

    ticker: str

    current_price: float

    forecast_price: float

    expected_move_pct: float

    confidence: int

    confidence_level: str

    horizon: int

    model: str

    details_available: bool