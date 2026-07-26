from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from internal_testing.environment import load_internal_testing_settings


ALLOWED_PLANS = {"free", "standard", "premium", "gold"}
ALLOWED_STATES = {"free", "pro", "expired", "trial", "cancelled"}
ALLOWED_EVENTS = {
    "new_subscription", "renewal", "cancellation", "expiration",
    "failed_payment", "trial_expiration", "downgrade", "upgrade",
}
STATE_PRESETS = {
    "free": ("free", "free"),
    "pro": ("premium", "active"),
    "expired": ("free", "expired"),
    "trial": ("premium", "trialing"),
    "cancelled": ("free", "canceled"),
}
ACTIVE_STATUSES = {"active", "trialing", "past_due"}


@dataclass(frozen=True)
class SubscriptionSnapshot:
    user_id: str
    plan: str
    subscription_status: str
    current_period_start: str | None
    current_period_end: str | None
    source: str
    scenario: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] | None = None


class InternalTestingDisabled(RuntimeError):
    pass


class SubscriptionTestingToolkit:
    """Local, ephemeral subscription state for approved non-production use."""

    def __init__(self, state_path: str | None = None) -> None:
        settings = load_internal_testing_settings()
        self.settings = settings
        self.path = Path(state_path or settings.state_path)
        self._lock = threading.RLock()

    def require_enabled(self) -> None:
        if not self.settings.enabled or self.settings.is_production:
            raise InternalTestingDisabled("Internal testing tools are disabled.")

    def _empty(self) -> dict[str, Any]:
        return {"version": 1, "overrides": {}, "simulations": {}, "test_clocks": {}}

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(payload, dict):
            return self._empty()
        baseline = self._empty()
        baseline.update(payload)
        return baseline

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def set_override(self, *, user_id: str, state: str, actor: str) -> dict[str, Any]:
        self.require_enabled()
        normalized = state.strip().lower()
        if normalized not in ALLOWED_STATES:
            raise ValueError(f"State must be one of: {', '.join(sorted(ALLOWED_STATES))}.")
        plan, status = STATE_PRESETS[normalized]
        now = self._now()
        snapshot = SubscriptionSnapshot(
            user_id=user_id,
            plan=plan,
            subscription_status=status,
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=30)).isoformat(),
            source="developer_override",
            scenario=normalized,
            updated_at=now.isoformat(),
            metadata={"actor": actor},
        )
        with self._lock:
            payload = self._load()
            payload["overrides"][user_id] = asdict(snapshot)
            self._save(payload)
        return asdict(snapshot)

    def clear_override(self, *, user_id: str) -> bool:
        self.require_enabled()
        with self._lock:
            payload = self._load()
            removed = payload["overrides"].pop(user_id, None) is not None
            self._save(payload)
        return removed

    def get_effective_snapshot(self, user_id: str) -> dict[str, Any] | None:
        if not self.settings.enabled or self.settings.is_production:
            return None
        with self._lock:
            payload = self._load()
            candidates = [
                value
                for value in (
                    payload["overrides"].get(user_id),
                    payload["simulations"].get(user_id),
                )
                if value
            ]
            if not candidates:
                return None
            return max(candidates, key=lambda item: str(item.get("updated_at") or ""))

    def simulate_event(
        self,
        *,
        user_id: str,
        event: str,
        actor: str,
        plan: str | None = None,
    ) -> dict[str, Any]:
        self.require_enabled()
        scenario = event.strip().lower()
        if scenario not in ALLOWED_EVENTS:
            raise ValueError(f"Unsupported scenario: {event}.")
        requested_plan = (plan or "premium").strip().lower()
        if requested_plan not in ALLOWED_PLANS:
            raise ValueError(f"Plan must be one of: {', '.join(sorted(ALLOWED_PLANS))}.")

        previous = self.get_effective_snapshot(user_id) or {}
        previous_plan = str(previous.get("plan") or "free")
        now = self._now()
        period_start = now
        period_end = now + timedelta(days=30)
        status = "active"
        effective_plan = requested_plan

        if scenario == "renewal":
            effective_plan = previous_plan if previous_plan in ALLOWED_PLANS else requested_plan
        elif scenario == "cancellation":
            effective_plan, status = "free", "canceled"
        elif scenario == "expiration":
            effective_plan, status, period_end = "free", "expired", now
        elif scenario == "failed_payment":
            effective_plan = previous_plan if previous_plan != "free" else requested_plan
            status = "past_due"
        elif scenario == "trial_expiration":
            effective_plan, status, period_end = "free", "trial_expired", now
        elif scenario == "downgrade":
            effective_plan = requested_plan if requested_plan != "gold" else "standard"
        elif scenario == "upgrade":
            effective_plan = requested_plan if requested_plan != "free" else "premium"

        if status not in ACTIVE_STATUSES:
            effective_plan = "free"

        snapshot = SubscriptionSnapshot(
            user_id=user_id,
            plan=effective_plan,
            subscription_status=status,
            current_period_start=period_start.isoformat(),
            current_period_end=period_end.isoformat(),
            source="admin_simulator",
            scenario=scenario,
            updated_at=now.isoformat(),
            metadata={"actor": actor, "requested_plan": requested_plan},
        )
        with self._lock:
            payload = self._load()
            payload["simulations"][user_id] = asdict(snapshot)
            self._save(payload)
        return asdict(snapshot)

    def reset(self, *, user_id: str | None = None) -> dict[str, int]:
        self.require_enabled()
        with self._lock:
            payload = self._load()
            if user_id:
                counts = {
                    "overrides": int(payload["overrides"].pop(user_id, None) is not None),
                    "simulations": int(payload["simulations"].pop(user_id, None) is not None),
                    "test_clocks": int(payload["test_clocks"].pop(user_id, None) is not None),
                }
                self._save(payload)
                return counts
            counts = {key: len(payload[key]) for key in ("overrides", "simulations", "test_clocks")}
            self._save(self._empty())
            return counts

    def save_test_clock(self, *, user_id: str, clock_id: str, frozen_time: int) -> None:
        self.require_enabled()
        with self._lock:
            payload = self._load()
            payload["test_clocks"][user_id] = {
                "clock_id": clock_id,
                "frozen_time": frozen_time,
                "updated_at": self._now().isoformat(),
            }
            self._save(payload)
