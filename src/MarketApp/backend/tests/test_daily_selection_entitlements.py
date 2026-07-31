from __future__ import annotations

import pytest

from services.entitlement_service import EntitlementError, EntitlementService


def _service(plan: str, status: str = "active") -> EntitlementService:
    service = EntitlementService.__new__(EntitlementService)
    service._profile_for_user = lambda user_id: {
        "id": user_id,
        "plan": plan,
        "subscription_status": status,
    }
    return service


def test_premium_is_authorized_for_locked_daily_selection() -> None:
    decision = _service("premium").authorize_daily_selection(user_id="user-1")
    assert decision["mode"] == "locked_selection"


def test_gold_is_authorized_for_simultaneous_forecasts() -> None:
    decision = _service("gold").authorize_daily_selection(user_id="user-1")
    assert decision["mode"] == "simultaneous"


def test_administrator_is_authorized_without_profile_lookup() -> None:
    service = EntitlementService.__new__(EntitlementService)
    decision = service.authorize_daily_selection(
        user_id="internal-admin",
        administrator=True,
    )
    assert decision["plan"] == "administrator"
    assert decision["mode"] == "simultaneous"


@pytest.mark.parametrize("plan", ["free", "standard"])
def test_non_premium_plans_are_rejected(plan: str) -> None:
    with pytest.raises(EntitlementError):
        _service(plan).authorize_daily_selection(user_id="user-1")


def test_inactive_premium_subscription_is_rejected() -> None:
    with pytest.raises(EntitlementError, match="active Premium or Gold"):
        _service("premium", status="expired").authorize_daily_selection(
            user_id="user-1"
        )
