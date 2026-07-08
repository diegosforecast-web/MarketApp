from typing import Any

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    """
    Standard response returned to the frontend.
    """

    ticker: str
    current_price: float
    forecast_price: float | None = None
    expected_move_pct: float
    confidence: int
    confidence_level: str
    horizon: int
    recommendation: str
    model: str
    details_available: bool
    reasons: list[str] = []
    warnings: list[str] = []
    explanation: dict[str, Any] | None = None
    historical_confidence: dict[str, Any] | None = None