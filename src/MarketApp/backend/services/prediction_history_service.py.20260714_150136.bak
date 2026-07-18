from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from services.market_data_service import MarketDataService
from services.prediction_verification_service import PredictionVerificationService
from services.supabase_service import SupabaseService


class PredictionHistoryService:
    def __init__(self) -> None:
        self.supabase = SupabaseService()
        self.verification = PredictionVerificationService()
        self.market_data = MarketDataService()

    @staticmethod
    def verification_due_at(created_at: datetime, horizon: int) -> datetime:
        due = created_at
        remaining = int(horizon)

        while remaining > 0:
            due += timedelta(days=1)
            if due.weekday() < 5:
                remaining -= 1

        return due

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).date()

    @classmethod
    def enrich_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row.get("response_json") or {})
        raw_created = row.get("created_at")
        created_at = (
            datetime.fromisoformat(str(raw_created).replace("Z", "+00:00"))
            if raw_created
            else datetime.now(timezone.utc)
        )

        horizon = int(row.get("horizon") or payload.get("horizon") or 1)
        trajectory = payload.get("trajectory") or []
        target_date = row.get("target_date") or (
            trajectory[-1].get("date") if trajectory else None
        )
        verify_at = (
            f"{target_date}T21:00:00+00:00"
            if target_date
            else cls.verification_due_at(created_at, horizon).isoformat()
        )

        stored_status = row.get("verification_status") or "pending"

        if stored_status == "verified":
            status = "verified"
        elif datetime.now(timezone.utc) >= datetime.fromisoformat(
            str(verify_at).replace("Z", "+00:00")
        ):
            status = "due"
        else:
            status = "pending"

        return {
            "id": row.get("id"),
            "ticker": row.get("ticker") or payload.get("ticker"),
            "horizon": horizon,
            "recommendation": row.get("recommendation") or payload.get("recommendation"),
            "confidence": row.get("confidence") or payload.get("confidence"),
            "expected_move_pct": (
                row.get("expected_move_pct")
                if row.get("expected_move_pct") is not None
                else payload.get("expected_move_pct")
            ),
            "created_at": created_at.isoformat(),
            "target_date": target_date,
            "verify_at": verify_at,
            "verification_status": status,
            "actual_price": row.get("actual_price"),
            "actual_move_pct": row.get("actual_move_pct"),
            "direction_correct": row.get("direction_correct"),
            "price_accuracy_pct": row.get("price_accuracy_pct"),
            "verified_at": row.get("verified_at"),
            "response": payload,
        }

    def record(self, *, user_id: str, prediction: Any) -> dict[str, Any]:
        payload = (
            prediction.model_dump()
            if hasattr(prediction, "model_dump")
            else dict(prediction)
        )
        saved = self.supabase.insert_prediction(
            user_id=user_id,
            payload=payload,
        )
        self.supabase.insert_usage(
            user_id=user_id,
            horizon=int(payload["horizon"]),
        )
        return self.enrich_row(saved)

    def list_for_user(
        self,
        *,
        user_id: str,
        limit: int = 50,
        verify_due: bool = True,
    ) -> list[dict[str, Any]]:
        if verify_due:
            self.verification.verify_due_for_user(
                user_id=user_id,
                limit=limit,
            )

        return [
            self.enrich_row(row)
            for row in self.supabase.list_predictions(
                user_id=user_id,
                limit=limit,
            )
        ]

    def get_for_user(
        self,
        *,
        user_id: str,
        prediction_id: str,
    ) -> dict[str, Any] | None:
        row = self.supabase.get_prediction(
            user_id=user_id,
            prediction_id=prediction_id,
        )

        if not row:
            return None

        if row.get("verification_status") != "verified":
            try:
                self.verification.verify_row(row)
                row = (
                    self.supabase.get_prediction(
                        user_id=user_id,
                        prediction_id=prediction_id,
                    )
                    or row
                )
            except Exception:
                pass

        return self.enrich_row(row)

    @staticmethod
    def _error_pct(
        predicted_price: float,
        actual_price: float,
    ) -> float | None:
        if actual_price <= 0:
            return None
        return abs(predicted_price - actual_price) / actual_price * 100

    def progress_for_user(
        self,
        *,
        user_id: str,
        prediction_id: str,
    ) -> dict[str, Any] | None:
        row = self.supabase.get_prediction(
            user_id=user_id,
            prediction_id=prediction_id,
        )

        if not row:
            return None

        item = self.enrich_row(row)
        response = item.get("response") or {}
        trajectory = sorted(
            [
                point
                for point in (response.get("trajectory") or [])
                if point.get("date") and point.get("price") is not None
            ],
            key=lambda point: int(point.get("day") or 0),
        )

        if not trajectory:
            return {
                "prediction_id": prediction_id,
                "available": False,
                "message": (
                    "This prediction was created before stored "
                    "trajectory tracking was available."
                ),
            }

        ticker = str(item.get("ticker") or "").strip().upper()

        if not ticker:
            return {
                "prediction_id": prediction_id,
                "available": False,
                "message": "The saved prediction has no ticker.",
            }

        market_history = self.market_data.get_history(ticker)
        today = datetime.now(timezone.utc).date()
        usable_history = market_history[
            market_history["date"].dt.date <= today
        ].copy()

        if usable_history.empty:
            return {
                "prediction_id": prediction_id,
                "available": False,
                "message": "No current market data is available yet.",
            }

        actual_by_date = {
            market_date.date(): float(close)
            for market_date, close in zip(
                usable_history["date"],
                usable_history["close"],
            )
        }

        latest_row = usable_history.iloc[-1]
        latest_actual_date = latest_row["date"].date()
        latest_actual_price = float(latest_row["close"])
        comparisons: list[dict[str, Any]] = []

        for point in trajectory:
            point_date = self._parse_date(point.get("date"))
            day_number = int(point.get("day") or 0)

            if point_date is None or point_date > latest_actual_date:
                continue

            actual_price = actual_by_date.get(point_date)
            actual_date = point_date

            if actual_price is None:
                later_dates = [
                    candidate
                    for candidate in actual_by_date
                    if point_date <= candidate <= latest_actual_date
                ]
                if not later_dates:
                    continue
                actual_date = min(later_dates)
                actual_price = actual_by_date[actual_date]

            predicted_price = float(point["price"])
            error = self._error_pct(predicted_price, actual_price)

            comparisons.append(
                {
                    "day": day_number,
                    "forecast_date": point_date.isoformat(),
                    "actual_date": actual_date.isoformat(),
                    "predicted_price": round(predicted_price, 4),
                    "actual_price": round(actual_price, 4),
                    "forecast_error_pct": (
                        round(error, 4) if error is not None else None
                    ),
                    "prediction_source": point.get("source"),
                }
            )

        forecast_points = [
            point
            for point in trajectory
            if int(point.get("day") or 0) > 0
        ]
        elapsed_points = [
            point
            for point in forecast_points
            if (
                self._parse_date(point.get("date"))
                and self._parse_date(point.get("date")) <= latest_actual_date
            )
        ]

        original_horizon = int(item.get("horizon") or len(forecast_points))
        elapsed_days = min(original_horizon, len(elapsed_points))
        remaining_days = max(0, original_horizon - elapsed_days)
        latest_comparison = comparisons[-1] if comparisons else None

        starting_price = float(
            response.get("current_price")
            or trajectory[0].get("price")
            or 0
        )
        actual_move_pct = (
            (latest_actual_price / starting_price - 1) * 100
            if starting_price > 0
            else None
        )

        checkpoint_days = {
            0,
            7,
            14,
            30,
            60,
            90,
            elapsed_days,
            original_horizon,
        }
        checkpoints = [
            comparison
            for comparison in comparisons
            if comparison["day"] in checkpoint_days
        ]

        if latest_comparison and latest_comparison not in checkpoints:
            checkpoints.append(latest_comparison)

        checkpoints.sort(key=lambda point: int(point["day"]))

        return {
            "prediction_id": prediction_id,
            "available": True,
            "ticker": ticker,
            "created_at": item.get("created_at"),
            "original_horizon": original_horizon,
            "confidence": item.get("confidence"),
            "verification_status": item.get("verification_status"),
            "target_date": item.get("target_date"),
            "elapsed_days": elapsed_days,
            "remaining_days": remaining_days,
            "status_label": (
                "Completed"
                if item.get("verification_status") == "verified"
                else (
                    f"Day {elapsed_days} of {original_horizon}"
                    if remaining_days > 0
                    else "Horizon reached"
                )
            ),
            "latest_actual_date": latest_actual_date.isoformat(),
            "latest_actual_price": round(latest_actual_price, 4),
            "actual_move_pct": (
                round(actual_move_pct, 4)
                if actual_move_pct is not None
                else None
            ),
            "forecast_error_so_far_pct": (
                latest_comparison.get("forecast_error_pct")
                if latest_comparison
                else None
            ),
            "latest_predicted_price": (
                latest_comparison.get("predicted_price")
                if latest_comparison
                else None
            ),
            "checkpoints": checkpoints,
        }

    def statistics_for_user(
        self,
        *,
        user_id: str,
        limit: int = 500,
    ) -> dict[str, Any]:
        items = self.list_for_user(
            user_id=user_id,
            limit=limit,
            verify_due=True,
        )
        verified = [
            item
            for item in items
            if item["verification_status"] == "verified"
        ]
        correct = [
            item
            for item in verified
            if item["direction_correct"] is True
        ]

        avg_confidence = (
            sum(float(item["confidence"] or 0) for item in items) / len(items)
            if items
            else 0.0
        )
        avg_price_accuracy = (
            sum(float(item["price_accuracy_pct"] or 0) for item in verified)
            / len(verified)
            if verified
            else 0.0
        )

        horizon_scores: dict[int, list[bool]] = {}

        for item in verified:
            horizon_scores.setdefault(
                int(item["horizon"]),
                [],
            ).append(bool(item["direction_correct"]))

        best_horizon = None

        if horizon_scores:
            best_horizon = max(
                horizon_scores,
                key=lambda horizon: (
                    sum(horizon_scores[horizon]) / len(horizon_scores[horizon]),
                    len(horizon_scores[horizon]),
                ),
            )

        return {
            "total_forecasts": len(items),
            "verified_forecasts": len(verified),
            "pending_forecasts": len(items) - len(verified),
            "correct_direction": len(correct),
            "direction_accuracy_pct": (
                round(len(correct) / len(verified) * 100, 2)
                if verified
                else 0.0
            ),
            "average_confidence_pct": round(avg_confidence, 2),
            "average_price_accuracy_pct": round(avg_price_accuracy, 2),
            "best_horizon": best_horizon,
        }
