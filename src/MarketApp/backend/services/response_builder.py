from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas.response import (
    ForecastCollection,
    ForecastTrajectoryPoint,
    PredictionResponse,
)


class ResponseBuilder:
    """Construct and authorize API responses after forecast generation."""

    _LOWEST_FORECAST_ENTITLEMENT = "lowest_forecast"
    _HIGHEST_FORECAST_ENTITLEMENT = "highest_forecast"

    @staticmethod
    def build_forecast_collection(
        *,
        expected_price: float | None,
        trajectory: list[ForecastTrajectoryPoint] | None = None,
    ) -> ForecastCollection | None:
        """Build an additive price collection from the existing forecast path.

        The collection reuses prices already produced by the forecast pipeline.
        It does not execute models or alter forecast generation. Day zero is
        excluded because it represents the current market price rather than a
        future expected price.
        """
        if expected_price is None:
            return None

        expected = round(float(expected_price), 2)
        future_prices = [
            round(float(point.price), 2)
            for point in trajectory or []
            if point.day > 0
        ]
        price_candidates = [expected, *future_prices]

        return ForecastCollection(
            lowest_expected_price=min(price_candidates),
            expected_price=expected,
            highest_expected_price=max(price_candidates),
        )

    @classmethod
    def filter_prediction_response(
        cls,
        *,
        response: PredictionResponse,
        authorization_context: Mapping[str, Any] | None,
    ) -> PredictionResponse:
        """Filter response composition using centralized entitlement results.

        The caller supplies capability decisions resolved by the entitlement
        service. The builder does not infer access from plan names. Omitting an
        authorization context preserves the existing response contract during
        migration.
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

        # The expected/average forecast remains available through the existing
        # forecast_price field. The additive collection is exposed only when
        # both range capabilities are authorized, avoiding partial or
        # misleading range objects.
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
        )

        return cls.filter_prediction_response(
            response=response,
            authorization_context=authorization_context,
        )
