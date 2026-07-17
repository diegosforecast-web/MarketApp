from __future__ import annotations

from datetime import date, datetime, timedelta

from ensemble.decision_engine import EnsembleDecisionEngine
from schemas.prediction import PredictionRequest
from schemas.response import ForecastTrajectoryPoint, PredictionResponse
from services.entitlement_service import EntitlementService
from services.market_data_service import MarketDataService
from services.prediction_history_service import PredictionHistoryService


class PredictionService:
    def __init__(self):
        self.market_data = MarketDataService()
        self.ensemble = EnsembleDecisionEngine()
        self.history = PredictionHistoryService()
        self.entitlements = EntitlementService()

    def supported_horizons(self) -> list[int]:
        return self.ensemble.supported_horizons()

    @staticmethod
    def _as_date(value) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        return datetime.fromisoformat(str(value)).date()

    @staticmethod
    def _next_trading_dates(
        start_date: date,
        number_of_days: int,
    ) -> list[date]:
        result: list[date] = []
        cursor = start_date

        while len(result) < number_of_days:
            cursor += timedelta(days=1)

            if cursor.weekday() < 5:
                result.append(cursor)

        return result

    def _build_trajectory(
        self,
        *,
        ticker: str,
        price_history,
        current_price: float,
        selected_horizon: int,
        final_decision,
    ) -> list[ForecastTrajectoryPoint]:
        supported = sorted(
            horizon
            for horizon in self.supported_horizons()
            if horizon <= selected_horizon
        )

        model_points: dict[int, dict] = {
            0: {
                "expected_return": 0.0,
                "direction_probability": 0.50,
                "confidence": "CURRENT",
                "recommendation": "CURRENT",
            },
            selected_horizon: {
                "expected_return": float(final_decision.expected_return),
                "direction_probability": float(
                    final_decision.direction_probability
                ),
                "confidence": final_decision.confidence,
                "recommendation": final_decision.recommendation,
            },
        }

        for horizon in supported:
            if horizon == selected_horizon:
                continue

            decision = self.ensemble.predict_point(
                ticker=ticker,
                price_df=price_history,
                horizon=horizon,
            )

            model_points[horizon] = {
                "expected_return": float(decision.expected_return),
                "direction_probability": float(
                    decision.direction_probability
                ),
                "confidence": decision.confidence,
                "recommendation": decision.recommendation,
            }

        latest_market_date = self._as_date(
            price_history["date"].iloc[-1]
        )
        trading_dates = self._next_trading_dates(
            latest_market_date,
            selected_horizon,
        )

        trajectory: list[ForecastTrajectoryPoint] = [
            ForecastTrajectoryPoint(
                day=0,
                date=latest_market_date.isoformat(),
                price=round(current_price, 2),
                expected_move_pct=0.0,
                confidence=50,
                confidence_level="CURRENT",
                recommendation="CURRENT",
                source="current",
            )
        ]

        known_days = sorted(model_points)

        for day in range(1, selected_horizon + 1):
            if day in model_points:
                point = model_points[day]
                source = "model"
            else:
                lower_day = max(
                    candidate
                    for candidate in known_days
                    if candidate < day
                )
                upper_day = min(
                    candidate
                    for candidate in known_days
                    if candidate > day
                )

                lower = model_points[lower_day]
                upper = model_points[upper_day]
                weight = (
                    (day - lower_day)
                    / (upper_day - lower_day)
                )

                expected_return = (
                    lower["expected_return"]
                    + (
                        upper["expected_return"]
                        - lower["expected_return"]
                    )
                    * weight
                )

                direction_probability = (
                    lower["direction_probability"]
                    + (
                        upper["direction_probability"]
                        - lower["direction_probability"]
                    )
                    * weight
                )

                interpolated_decision = self.ensemble.decide(
                    ticker=ticker,
                    direction_probability=direction_probability,
                    expected_return=expected_return,
                )

                point = {
                    "expected_return": expected_return,
                    "direction_probability": direction_probability,
                    "confidence": interpolated_decision.confidence,
                    "recommendation": (
                        interpolated_decision.recommendation
                    ),
                }
                source = "interpolated"

            expected_return = float(point["expected_return"])
            probability = float(point["direction_probability"])
            recommendation = str(point["recommendation"])
            signal_probability = self.ensemble.signal_probability(
                probability,
                recommendation,
            )

            trajectory.append(
                ForecastTrajectoryPoint(
                    day=day,
                    date=trading_dates[day - 1].isoformat(),
                    price=round(
                        current_price * (1 + expected_return),
                        2,
                    ),
                    expected_move_pct=round(
                        expected_return * 100,
                        2,
                    ),
                    confidence=int(
                        round(signal_probability * 100)
                    ),
                    confidence_level=str(point["confidence"]),
                    recommendation=recommendation,
                    source=source,
                )
            )

        return trajectory

    async def predict(
        self,
        request: PredictionRequest,
        *,
        user_id: str,
    ) -> dict:
        ticker = request.ticker.strip().upper()
        horizon = int(request.horizon)
        supported = self.supported_horizons()

        # Must happen before market-data calls or model execution.
        self.entitlements.authorize(
            user_id=user_id,
            requested_horizon=horizon,
            supported_horizons=supported,
        )

        history = self.market_data.get_history(ticker)

        if history.empty:
            raise RuntimeError(
                f"No market data returned for {ticker}."
            )

        current_price = float(history["close"].iloc[-1])

        decision = self.ensemble.predict(
            ticker=ticker,
            price_df=history,
            horizon=horizon,
        )

        trajectory = self._build_trajectory(
            ticker=ticker,
            price_history=history,
            current_price=current_price,
            selected_horizon=horizon,
            final_decision=decision,
        )

        response = PredictionResponse(
            ticker=ticker,
            current_price=round(current_price, 2),
            forecast_price=round(
                current_price * (1 + decision.expected_return),
                2,
            ),
            expected_move_pct=round(
                decision.expected_return * 100,
                2,
            ),
            confidence=int(
                round(
                    self.ensemble.signal_probability(
                        decision.direction_probability,
                        decision.recommendation,
                    )
                    * 100
                )
            ),
            confidence_level=decision.confidence,
            horizon=horizon,
            recommendation=decision.recommendation,
            model=f"EnsembleDecisionEngine_h{horizon}",
            details_available=True,
            reasons=decision.reasons,
            warnings=decision.warnings,
            explanation=decision.explanation,
            historical_confidence=decision.historical_confidence,
            trajectory=trajectory,
        )

        saved = self.history.record(
            user_id=user_id,
            prediction=response,
        )

        # Re-read after the successful usage insert so the frontend receives
        # the new remaining balance immediately.
        updated_entitlements = self.entitlements.get_entitlements(
            user_id=user_id,
            supported_horizons=supported,
        )

        payload = response.model_dump()
        payload.update(
            {
                "prediction_id": saved["id"],
                "created_at": saved["created_at"],
                "verify_at": saved["verify_at"],
                "verification_status": (
                    saved["verification_status"]
                ),
                "entitlements": updated_entitlements,
            }
        )

        return payload
