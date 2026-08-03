from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class ForecastTrajectoryPoint(BaseModel):
    day: int
    date: str
    price: float
    expected_move_pct: float
    confidence: int
    confidence_level: str
    recommendation: str
    source: str


class ForecastCollection(BaseModel):
    lowest_expected_price: float
    expected_price: float
    highest_expected_price: float


class ForecastPresentation(BaseModel):
    mode: Literal["legacy", "locked_selection", "simultaneous"]
    selection: Literal["lowest", "expected", "highest"] | None = None
    display_price: float | None = None
    market_day: date | None = None
    locked: bool = False


class PredictionResponse(BaseModel):
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
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: dict[str, Any] | None = None
    historical_confidence: dict[str, Any] | None = None
    trajectory: list[ForecastTrajectoryPoint] = Field(default_factory=list)
    forecast_collection: ForecastCollection | None = None
    forecast_presentation: ForecastPresentation | None = None
