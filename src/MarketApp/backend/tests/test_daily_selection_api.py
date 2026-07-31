from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from endpoints.daily_selection import get_daily_selection_service, router
from services.auth_service import AuthenticatedUser, get_authenticated_user
from services.daily_selection_service import (
    DailySelectionLocked,
    DailySelectionUnauthorized,
)


class FakeService:
    def __init__(self) -> None:
        self.selection = None

    def get_active(self, *, user_id: str, market_day=None, administrator=False):
        return {
            "mode": "locked_selection",
            "market_day": market_day or "2026-07-30",
            "selection": self.selection,
            "locked": self.selection is not None,
            "record": None,
            "available_selections": ["lowest", "expected", "highest"],
        }

    def select(self, *, user_id: str, selection: str, market_day=None, administrator=False):
        if self.selection and self.selection != selection:
            raise DailySelectionLocked(
                {
                    "selection": self.selection,
                    "market_day": "2026-07-30",
                }
            )
        self.selection = selection
        return {
            "mode": "locked_selection",
            "market_day": market_day or "2026-07-30",
            "selection": selection,
            "locked": True,
            "record": None,
            "available_selections": ["lowest", "expected", "highest"],
        }


class UnauthorizedService(FakeService):
    def get_active(self, **kwargs):
        raise DailySelectionUnauthorized("Premium access is required.")


service = FakeService()
app = FastAPI()
app.include_router(router, prefix="/daily-selection")
app.dependency_overrides[get_authenticated_user] = lambda: AuthenticatedUser(
    id="user-1",
    email="user@example.com",
)
app.dependency_overrides[get_daily_selection_service] = lambda: service
client = TestClient(app)


def setup_function() -> None:
    service.selection = None


def test_put_then_get_daily_selection() -> None:
    response = client.put(
        "/daily-selection/",
        json={"selection": "expected", "market_day": "2026-07-30"},
    )
    assert response.status_code == 200
    assert response.json()["selection"] == "expected"
    assert response.json()["locked"] is True

    active = client.get("/daily-selection/?market_day=2026-07-30")
    assert active.status_code == 200
    assert active.json()["selection"] == "expected"


def test_changing_locked_selection_returns_conflict() -> None:
    client.put(
        "/daily-selection/",
        json={"selection": "lowest", "market_day": "2026-07-30"},
    )
    response = client.put(
        "/daily-selection/",
        json={"selection": "highest", "market_day": "2026-07-30"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["existing_selection"] == "lowest"


def test_unauthorized_access_returns_forbidden() -> None:
    app.dependency_overrides[get_daily_selection_service] = lambda: UnauthorizedService()
    try:
        response = client.get("/daily-selection/?market_day=2026-07-30")
        assert response.status_code == 403
    finally:
        app.dependency_overrides[get_daily_selection_service] = lambda: service


def test_invalid_selection_is_rejected_by_schema() -> None:
    response = client.put(
        "/daily-selection/",
        json={"selection": "median", "market_day": "2026-07-30"},
    )
    assert response.status_code == 422
