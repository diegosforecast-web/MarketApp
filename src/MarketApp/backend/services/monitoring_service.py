from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any


class MonitoringService:
    """
    Lightweight in-process application metrics for DiMarket v1.

    Metrics reset whenever the backend process restarts. This is intentional
    for v1 and avoids adding Prometheus, Redis, or another external service.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc)
        self._requests_total = 0
        self._requests_success = 0
        self._requests_failed = 0
        self._total_response_ms = 0.0

    def record_request(
        self,
        *,
        status_code: int,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self._requests_total += 1
            self._total_response_ms += max(
                0.0,
                float(duration_ms),
            )

            if int(status_code) < 400:
                self._requests_success += 1
            else:
                self._requests_failed += 1

    def snapshot(
        self,
        *,
        version: str,
        environment: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        with self._lock:
            total = self._requests_total
            success = self._requests_success
            failed = self._requests_failed
            total_response_ms = self._total_response_ms
            started_at = self._started_at

        uptime_seconds = max(
            0,
            int((now - started_at).total_seconds()),
        )

        average_response_ms = (
            total_response_ms / total
            if total
            else 0.0
        )

        success_rate_pct = (
            success / total * 100
            if total
            else 100.0
        )

        return {
            "status": "ok",
            "version": version,
            "environment": environment,
            "active_since": started_at.isoformat(),
            "uptime_seconds": uptime_seconds,
            "requests_total": total,
            "requests_success": success,
            "requests_failed": failed,
            "success_rate_pct": round(
                success_rate_pct,
                2,
            ),
            "average_response_ms": round(
                average_response_ms,
                2,
            ),
        }


monitoring_service = MonitoringService()
