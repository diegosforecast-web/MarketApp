from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from schemas.response import (
    ForecastCollection,
    ForecastPresentation,
    ForecastTrajectoryPoint,
    PredictionResponse,
)


class ResponseBuilder:
    """Construct and authorize API responses after forecast generation."""

    _LOWEST_FORECAST_ENTITLEMENT = "lowest_forecast"
    _HIGHEST_FORECAST_ENTITLEMENT = "highest_forecast"
    _SELECTION_FIELD_MAP = {
        "lowest": "lowest_expected_price",
        "expected": "expected_price",
        "highest": "highest_expected_price",
    }

    @staticmethod
    def build_forecast_collection(
        *,
        expected_price: float | None,
        lower_price: float | None = None,
        upper_price: float | None = None,
        calibration: Mapping[str, Any] | None = None,
    ) -> ForecastCollection | None:
        """Build calibrated lower, expected, and upper forecast bounds.

        Bounds must be supplied by the forecast-calibration layer. The response
        builder does not infer ranges from trajectories or presentation logic.
        Invalid or unavailable calibration fails closed by returning no
        collection while preserving the legacy expected forecast separately.
        """
        if expected_price is None or lower_price is None or upper_price is None:
            return None

        expected = round(float(expected_price), 2)
        lower = round(float(lower_price), 2)
        upper = round(float(upper_price), 2)

        if lower <= 0 or not lower <= expected <= upper:
            return None

        return ForecastCollection(
            lowest_expected_price=lower,
            expected_price=expected,
            highest_expected_price=upper,
            calibration=dict(calibration or {}) or None,
        )

    @classmethod
    def build_forecast_presentation(
        cls,
        *,
        forecast_price: float | None,
        forecast_collection: ForecastCollection | None,
        daily_selection_state: Mapping[str, Any] | None = None,
    ) -> ForecastPresentation:
        """Resolve the backend-authoritative forecast presentation.

        The daily-selection service supplies mode, selection, market day, and
        lock state. This method only maps that resolved state to prices already
        produced by the forecast pipeline.
        """
        fallback_price = (
            round(float(forecast_price), 2)
            if forecast_price is not None
            else None
        )

        if not daily_selection_state:
            return ForecastPresentation(
                mode="legacy",
                display_price=fallback_price,
            )

        mode = str(daily_selection_state.get("mode") or "legacy")
        market_day = daily_selection_state.get("market_day")
        if market_day is not None and not isinstance(market_day, date):
            market_day = date.fromisoformat(str(market_day))

        if mode == "simultaneous":
            display_price = (
                forecast_collection.expected_price
                if forecast_collection is not None
                else fallback_price
            )
            return ForecastPresentation(
                mode="simultaneous",
                display_price=display_price,
                market_day=market_day,
                locked=bool(daily_selection_state.get("locked", False)),
            )

        if mode == "locked_selection":
            raw_selection = daily_selection_state.get("selection")
            selection = (
                str(raw_selection).strip().lower()
                if raw_selection is not None
                else None
            )
            if selection not in cls._SELECTION_FIELD_MAP:
                selection = None

            display_price = fallback_price
            if selection and forecast_collection is not None:
                display_price = getattr(
                    forecast_collection,
                    cls._SELECTION_FIELD_MAP[selection],
                )

            return ForecastPresentation(
                mode="locked_selection",
                selection=selection,
                display_price=display_price,
                market_day=market_day,
                locked=bool(daily_selection_state.get("locked", False)),
            )

        return ForecastPresentation(
            mode="legacy",
            display_price=fallback_price,
        )

    @classmethod
    def authorization_context_for_presentation(
        cls,
        daily_selection_state: Mapping[str, Any] | None,
    ) -> dict[str, bool]:
        """Expose the complete collection only for simultaneous presentation."""
        simultaneous = bool(
            daily_selection_state
            and daily_selection_state.get("mode") == "simultaneous"
        )
        return {
            cls._LOWEST_FORECAST_ENTITLEMENT: simultaneous,
            cls._HIGHEST_FORECAST_ENTITLEMENT: simultaneous,
        }

    @classmethod
    def filter_prediction_response(
        cls,
        *,
        response: PredictionResponse,
        authorization_context: Mapping[str, Any] | None,
    ) -> PredictionResponse:
        """Filter response composition using centralized entitlement results.

        The caller supplies capability decisions resolved by the entitlement
        and daily-selection services. The builder does not infer access from
        plan names. Omitting an authorization context preserves the existing
        response contract during migration.
        """
        filtered = response.model_copy(deep=True)

        if authorization_context is None:
            return filtered

        can_view_lowest = bool(
            authorization_context.get(
                cls._LOWEST_FORECAST_ENTITLEMENT,
                False,
            )
        )
        can_view_highest = bool(
            authorization_context.get(
                cls._HIGHEST_FORECAST_ENTITLEMENT,
                False,
            )
        )

        if not (can_view_lowest and can_view_highest):
            filtered.forecast_collection = None

        return filtered

    @classmethod
    def build_prediction_response(
        cls,
        *,
        ticker: str,
        current_price: float,
        forecast_price: float | None,
        expected_move_pct: float,
        confidence: int,
        confidence_level: str,
        horizon: int,
        recommendation: str,
        model: str,
        details_available: bool,
        reasons: list[str] | None = None,
        warnings: list[str] | None = None,
        explanation: dict[str, Any] | None = None,
        historical_confidence: dict[str, Any] | None = None,
        trajectory: list[ForecastTrajectoryPoint] | None = None,
        forecast_collection: ForecastCollection | None = None,
        forecast_presentation: ForecastPresentation | None = None,
        authorization_context: Mapping[str, Any] | None = None,
    ) -> PredictionResponse:
        """Build, then authorization-filter, a backward-compatible response."""
        response = PredictionResponse(
            ticker=ticker,
            current_price=current_price,
            forecast_price=forecast_price,
            expected_move_pct=expected_move_pct,
            confidence=confidence,
            confidence_level=confidence_level,
            horizon=horizon,
            recommendation=recommendation,
            model=model,
            details_available=details_available,
            reasons=list(reasons or []),
            warnings=list(warnings or []),
            explanation=explanation,
            historical_confidence=historical_confidence,
            trajectory=list(trajectory or []),
            forecast_collection=forecast_collection,
            forecast_presentation=forecast_presentation,
        )

        return cls.filter_prediction_response(
            response=response,
            authorization_context=authorization_context,
        )
