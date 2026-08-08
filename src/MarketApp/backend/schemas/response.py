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


class ForecastCalibrationMetadata(BaseModel):
    method: str
    model_task: str
    model_version: str
    model_file: str | None = None
    horizon: int
    lower_quantile: float
    upper_quantile: float
    intended_coverage: float
    sample_count: int
    validation_sample_count: int | None = None
    calibration_start: str
    calibration_end: str
    validation_start: str | None = None
    validation_end: str | None = None
    generated_at: str
    empirical_coverage: float | None = None
    average_interval_width: float | None = None
    median_interval_width: float | None = None
    residual_definition: str | None = None
    reference_ticker: str | None = None
    training_cutoff: str | None = None
    evaluation_tickers: list[str] = Field(default_factory=list)
    provenance: str | None = None
    calibration_diagnostics: dict[str, float] | None = None
    validation_diagnostics: dict[str, float] | None = None


class ForecastCollection(BaseModel):
    lowest_expected_price: float
    expected_price: float
    highest_expected_price: float
    calibration: ForecastCalibrationMetadata | None = None


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
