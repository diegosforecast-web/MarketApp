from __future__ import annotations

import os
import time
from typing import Any

import stripe

from internal_testing.environment import load_internal_testing_settings
from internal_testing.subscription_toolkit import SubscriptionTestingToolkit


class StripeTestClockUnavailable(RuntimeError):
    pass


class StripeTestClockService:
    def __init__(self, toolkit: SubscriptionTestingToolkit | None = None) -> None:
        self.settings = load_internal_testing_settings()
        self.toolkit = toolkit or SubscriptionTestingToolkit()

    def _require_available(self) -> None:
        self.toolkit.require_enabled()
        key = os.getenv("STRIPE_SECRET_KEY", "")
        explicit = os.getenv("ENABLE_STRIPE_TEST_CLOCKS", "false").strip().lower() in {
            "1", "true", "yes", "on"
        }
        if not explicit or not key.startswith("sk_test_"):
            raise StripeTestClockUnavailable(
                "Stripe Test Clocks require ENABLE_STRIPE_TEST_CLOCKS=true and a Stripe test secret key."
            )
        if not hasattr(stripe, "test_helpers") or not hasattr(stripe.test_helpers, "TestClock"):
            raise StripeTestClockUnavailable("The installed Stripe SDK does not support Test Clocks.")
        stripe.api_key = key

    @staticmethod
    def _value(obj: Any, key: str, default: Any = None) -> Any:
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    def create(self, *, user_id: str, name: str | None = None) -> dict[str, Any]:
        self._require_available()
        clock = stripe.test_helpers.TestClock.create(
            frozen_time=int(time.time()),
            name=name or f"DiMarket QA {user_id}",
        )
        clock_id = str(self._value(clock, "id"))
        frozen_time = int(self._value(clock, "frozen_time"))
        self.toolkit.save_test_clock(user_id=user_id, clock_id=clock_id, frozen_time=frozen_time)
        return {"id": clock_id, "frozen_time": frozen_time, "status": self._value(clock, "status")}

    def advance(self, *, user_id: str, clock_id: str, frozen_time: int) -> dict[str, Any]:
        self._require_available()
        clock = stripe.test_helpers.TestClock.advance(clock_id, frozen_time=frozen_time)
        actual = int(self._value(clock, "frozen_time", frozen_time))
        self.toolkit.save_test_clock(user_id=user_id, clock_id=clock_id, frozen_time=actual)
        return {"id": str(self._value(clock, "id", clock_id)), "frozen_time": actual, "status": self._value(clock, "status")}
