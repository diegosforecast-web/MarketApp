from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from services.daily_selection_service import (
    DailySelectionLocked,
    DailySelectionService,
    DailySelectionUnauthorized,
)
from services.entitlement_service import EntitlementError


class FakeRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, date], dict] = {}
        self.create_count = 0

    def get(self, *, user_id: str, market_day: date):
        return self.rows.get((user_id, market_day))

    def create(self, *, user_id: str, market_day: date, selection: str):
        self.create_count += 1
        row = {
            "id": f"selection-{self.create_count}",
            "user_id": user_id,
            "market_day": market_day.isoformat(),
            "selection": selection,
            "locked_at": "2026-07-30T14:00:00+00:00",
            "created_at": "2026-07-30T14:00:00+00:00",
        }
        existing = self.rows.setdefault((user_id, market_day), row)
        return existing


class FakeEntitlements:
    def __init__(self, mode: str | None) -> None:
        self.mode = mode

    def authorize_daily_selection(self, *, user_id: str, administrator: bool = False):
        if administrator:
            return {"allowed": True, "mode": "simultaneous", "plan": "administrator"}
        if self.mode is None:
            raise EntitlementError(
                "Premium Daily Selection requires a Premium or Gold plan.",
                entitlements={"plan": "standard"},
            )
        return {"allowed": True, "mode": self.mode, "plan": "premium"}


def _service(mode: str | None = "locked_selection") -> tuple[DailySelectionService, FakeRepository]:
    repository = FakeRepository()
    service = DailySelectionService(
        repository=repository,
        entitlement_service=FakeEntitlements(mode),
        now_provider=lambda: datetime(
            2026,
            7,
            30,
            10,
            0,
            tzinfo=ZoneInfo("America/New_York"),
        ),
    )
    return service, repository


def test_premium_selection_is_persisted_and_locked() -> None:
    service, repository = _service()

    result = service.select(user_id="user-1", selection="expected")

    assert result["selection"] == "expected"
    assert result["locked"] is True
    assert result["market_day"] == date(2026, 7, 30)
    assert repository.create_count == 1


def test_same_selection_is_idempotent() -> None:
    service, repository = _service()

    first = service.select(user_id="user-1", selection="highest")
    second = service.select(user_id="user-1", selection="highest")

    assert second["record"] == first["record"]
    assert repository.create_count == 1


def test_locked_selection_cannot_be_changed() -> None:
    service, _ = _service()
    service.select(user_id="user-1", selection="lowest")

    with pytest.raises(DailySelectionLocked) as error:
        service.select(user_id="user-1", selection="highest")

    assert error.value.existing["selection"] == "lowest"


def test_active_selection_is_retrieved_deterministically() -> None:
    service, _ = _service()
    service.select(user_id="user-1", selection="expected")

    active = service.get_active(user_id="user-1")

    assert active["mode"] == "locked_selection"
    assert active["selection"] == "expected"
    assert active["locked"] is True


def test_selections_are_independent_by_user_and_market_day() -> None:
    service, repository = _service()
    day_one = date(2026, 7, 30)
    day_two = date(2026, 7, 31)

    service.select(user_id="user-1", selection="lowest", market_day=day_one)
    service.select(user_id="user-1", selection="highest", market_day=day_two)
    service.select(user_id="user-2", selection="expected", market_day=day_one)

    assert repository.create_count == 3


def test_standard_or_explorer_is_not_authorized() -> None:
    service, repository = _service(mode=None)

    with pytest.raises(DailySelectionUnauthorized):
        service.select(user_id="user-1", selection="expected")

    assert repository.create_count == 0


def test_gold_receives_simultaneous_mode_without_lock() -> None:
    service, repository = _service(mode="simultaneous")

    result = service.select(user_id="gold-user", selection="lowest")

    assert result["mode"] == "simultaneous"
    assert result["selection"] is None
    assert result["locked"] is False
    assert repository.create_count == 0


def test_administrator_receives_simultaneous_mode_without_lock() -> None:
    service, repository = _service(mode=None)

    result = service.select(
        user_id="administrator",
        selection="highest",
        administrator=True,
    )

    assert result["mode"] == "simultaneous"
    assert repository.create_count == 0


def test_weekend_market_day_is_rejected() -> None:
    service, repository = _service()

    with pytest.raises(ValueError, match="weekday market day"):
        service.select(
            user_id="user-1",
            selection="expected",
            market_day=date(2026, 8, 1),
        )

    assert repository.create_count == 0


def test_invalid_selection_is_rejected() -> None:
    service, repository = _service()

    with pytest.raises(ValueError, match="lowest, expected, highest"):
        service.select(user_id="user-1", selection="median")

    assert repository.create_count == 0
