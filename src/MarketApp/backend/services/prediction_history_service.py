from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from services.market_data_service import MarketDataService
from services.prediction_verification_service import PredictionVerificationService
from services.supabase_service import SupabaseService
from services.datetime_utils import parse_iso_datetime


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
        return parse_iso_datetime(
            str(value).replace("Z", "+00:00")
        ).date()

    @classmethod
    def enrich_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row.get("response_json") or {})
        raw_created = row.get("created_at")
        created_at = (
            parse_iso_datetime(str(raw_created).replace("Z", "+00:00"))
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
        elif datetime.now(timezone.utc) >= parse_iso_datetime(
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
            "is_hidden": bool(row.get("is_hidden", False)),
            "details_purged": bool(row.get("details_purged", False)),
            "intraday_target_reached": row.get("intraday_target_reached"),
            "intraday_target_reached_at": row.get("intraday_target_reached_at"),
            "intraday_target_price": row.get("intraday_target_price"),
            "intraday_closest_price": row.get("intraday_closest_price"),
            "intraday_closest_at": row.get("intraday_closest_at"),
            "intraday_checked_at": row.get("intraday_checked_at"),
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
        include_hidden: bool = False,
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
                include_hidden=include_hidden,
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

    def set_visibility(
        self,
        *,
        user_id: str,
        prediction_id: str,
        is_hidden: bool,
    ) -> dict[str, Any] | None:
        updated = self.supabase.update_prediction_visibility(
            user_id=user_id,
            prediction_id=prediction_id,
            is_hidden=is_hidden,
        )
        return self.enrich_row(updated) if updated else None

    def purge_details(
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
            raise ValueError(
                "Only completed verified predictions can have detailed data deleted."
            )

        response = row.get("response_json") or {}

        compact_response = {
            "ticker": row.get("ticker") or response.get("ticker"),
            "horizon": row.get("horizon") or response.get("horizon"),
            "recommendation": (
                row.get("recommendation")
                or response.get("recommendation")
            ),
            "confidence": (
                row.get("confidence")
                or response.get("confidence")
            ),
            "current_price": response.get("current_price"),
            "forecast_price": response.get("forecast_price"),
            "expected_move_pct": (
                row.get("expected_move_pct")
                if row.get("expected_move_pct") is not None
                else response.get("expected_move_pct")
            ),
            "model": response.get("model"),
        }

        updated = self.supabase.purge_prediction_details(
            user_id=user_id,
            prediction_id=prediction_id,
            compact_response=compact_response,
        )

        return self.enrich_row(updated) if updated else None

    def refresh_intraday(
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

        self.verification.check_intraday_target(row)

        refreshed = self.supabase.get_prediction(
            user_id=user_id,
            prediction_id=prediction_id,
        )

        return self.enrich_row(refreshed) if refreshed else None

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
                    "Detailed forecast data is no longer available "
                    "for this completed prediction."
                    if item.get("details_purged")
                    else (
                        "This prediction was created before stored "
                        "trajectory tracking was available."
                    )
                ),
                "intraday_target_reached": item.get(
                    "intraday_target_reached"
                ),
                "intraday_target_reached_at": item.get(
                    "intraday_target_reached_at"
                ),
                "intraday_target_price": item.get(
                    "intraday_target_price"
                ),
                "intraday_closest_price": item.get(
                    "intraday_closest_price"
                ),
                "intraday_closest_at": item.get(
                    "intraday_closest_at"
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
            "intraday_target_reached": item.get(
                "intraday_target_reached"
            ),
            "intraday_target_reached_at": item.get(
                "intraday_target_reached_at"
            ),
            "intraday_target_price": item.get(
                "intraday_target_price"
            ),
            "intraday_closest_price": item.get(
                "intraday_closest_price"
            ),
            "intraday_closest_at": item.get(
                "intraday_closest_at"
            ),
            "intraday_checked_at": item.get(
                "intraday_checked_at"
            ),
            "checkpoints": checkpoints,
        }


    @staticmethod
    def _model_health(
        *,
        verified: list[dict[str, Any]],
        direction_accuracy: float,
        average_price_accuracy: float,
    ) -> dict[str, Any]:
        """
        Produce an evidence-based model-health summary.

        This is not statistical feature-distribution drift detection.
        It summarizes verified forecast performance only.

        Score weights:
        - Direction accuracy: 45%
        - Price accuracy: 25%
        - Confidence alignment: 20%
        - Recent performance stability: 10%
        """
        sample_size = len(verified)

        if sample_size < 5:
            return {
                "score": None,
                "status": "BUILDING EVIDENCE",
                "trend": "INSUFFICIENT DATA",
                "stability_index": None,
                "confidence_alignment_pct": None,
                "verified_sample_size": sample_size,
                "minimum_sample_size": 5,
                "retraining_recommendation": "NOT ASSESSED",
                "summary": (
                    "DiMarket is still building a sufficient verified "
                    "forecast history. At least five verified forecasts "
                    "are required before a model-health score is shown."
                ),
                "methodology": (
                    "Verified-outcome monitoring; not feature-distribution "
                    "drift detection."
                ),
            }

        ordered = sorted(
            verified,
            key=lambda item: parse_iso_datetime(
                item.get("verified_at")
                or item.get("created_at")
            ),
        )

        confidences = [
            float(item.get("confidence") or 0)
            for item in ordered
        ]

        outcomes = [
            100.0 if item.get("direction_correct") is True else 0.0
            for item in ordered
        ]

        average_verified_confidence = (
            sum(confidences) / sample_size
        )

        confidence_alignment = max(
            0.0,
            100.0
            - abs(
                average_verified_confidence
                - direction_accuracy
            ),
        )

        comparison_size = min(
            30,
            sample_size // 2,
        )

        if comparison_size >= 3:
            recent = outcomes[-comparison_size:]
            previous = outcomes[
                -(comparison_size * 2):-comparison_size
            ]

            recent_accuracy = sum(recent) / len(recent)
            previous_accuracy = (
                sum(previous) / len(previous)
                if previous
                else recent_accuracy
            )

            change = recent_accuracy - previous_accuracy

            if change >= 5.0:
                trend = "IMPROVING"
            elif change <= -5.0:
                trend = "DECLINING"
            else:
                trend = "STABLE"

            stability_index = max(
                0.0,
                100.0 - min(100.0, abs(change) * 2.0),
            )
        else:
            recent_accuracy = direction_accuracy
            previous_accuracy = direction_accuracy
            change = 0.0
            trend = "EARLY EVIDENCE"
            stability_index = 75.0

        score = round(
            direction_accuracy * 0.45
            + average_price_accuracy * 0.25
            + confidence_alignment * 0.20
            + stability_index * 0.10
        )

        score = max(0, min(100, score))

        if score >= 85:
            status = "EXCELLENT"
        elif score >= 75:
            status = "GOOD"
        elif score >= 60:
            status = "MONITOR"
        else:
            status = "NEEDS ATTENTION"

        if (
            sample_size >= 20
            and trend == "DECLINING"
            and score < 60
        ):
            retraining = "REVIEW RECOMMENDED"
        elif trend == "DECLINING":
            retraining = "CONTINUE MONITORING"
        else:
            retraining = "NOT CURRENTLY INDICATED"

        summary_parts = [
            (
                f"DiMarket's verified model-health score is "
                f"{score}/100, rated {status.lower()}."
            ),
            (
                f"This assessment uses {sample_size} verified "
                f"forecast{'s' if sample_size != 1 else ''}."
            ),
            (
                f"Recent verified performance is "
                f"{trend.lower().replace('_', ' ')}."
            ),
        ]

        if retraining == "NOT CURRENTLY INDICATED":
            summary_parts.append(
                "Current verified evidence does not indicate that "
                "retraining is necessary."
            )
        elif retraining == "CONTINUE MONITORING":
            summary_parts.append(
                "Recent performance should continue to be monitored "
                "before considering retraining."
            )
        else:
            summary_parts.append(
                "A structured model review is recommended before any "
                "candidate retraining or promotion."
            )

        return {
            "score": score,
            "status": status,
            "trend": trend,
            "stability_index": round(
                stability_index,
                2,
            ),
            "confidence_alignment_pct": round(
                confidence_alignment,
                2,
            ),
            "verified_sample_size": sample_size,
            "minimum_sample_size": 5,
            "recent_direction_accuracy_pct": round(
                recent_accuracy,
                2,
            ),
            "previous_direction_accuracy_pct": round(
                previous_accuracy,
                2,
            ),
            "recent_change_pct_points": round(
                change,
                2,
            ),
            "retraining_recommendation": retraining,
            "summary": " ".join(summary_parts),
            "methodology": (
                "Weighted verified-outcome monitoring: direction "
                "accuracy 45%, price accuracy 25%, confidence "
                "alignment 20%, recent stability 10%. This is not "
                "feature-distribution drift detection."
            ),
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
            include_hidden=True,
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

        direction_accuracy = (
            len(correct) / len(verified) * 100
            if verified
            else 0.0
        )

        model_health = self._model_health(
            verified=verified,
            direction_accuracy=direction_accuracy,
            average_price_accuracy=avg_price_accuracy,
        )

        return {
            "total_forecasts": len(items),
            "verified_forecasts": len(verified),
            "pending_forecasts": len(items) - len(verified),
            "correct_direction": len(correct),
            "direction_accuracy_pct": round(
                direction_accuracy,
                2,
            ),
            "average_confidence_pct": round(avg_confidence, 2),
            "average_price_accuracy_pct": round(
                avg_price_accuracy,
                2,
            ),
            "best_horizon": best_horizon,
            "model_health": model_health,
        }
