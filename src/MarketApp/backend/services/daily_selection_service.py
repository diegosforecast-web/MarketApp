from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Protocol
from zoneinfo import ZoneInfo

from services.entitlement_service import EntitlementError, EntitlementService
from services.supabase_service import SupabaseService


MARKET_TIMEZONE = ZoneInfo("America/New_York")
ALLOWED_SELECTIONS = {"lowest", "expected", "highest"}


class DailySelectionError(ValueError):
    pass


class DailySelectionUnauthorized(DailySelectionError):
    pass


class DailySelectionLocked(DailySelectionError):
    def __init__(self, existing: dict[str, Any]) -> None:
        super().__init__(
            "The Premium forecast selection is already locked for this market day."
        )
        self.existing = existing


class DailySelectionRepository(Protocol):
    def get(self, *, user_id: str, market_day: date) -> dict[str, Any] | None: ...

    def create(
        self,
        *,
        user_id: str,
        market_day: date,
        selection: str,
    ) -> dict[str, Any]: ...


class SupabaseDailySelectionRepository:
    COLUMNS = "id,user_id,market_day,selection,locked_at,created_at"

    def __init__(self, supabase: SupabaseService | None = None) -> None:
        self.supabase = supabase or SupabaseService()

    def get(
        self,
        *,
        user_id: str,
        market_day: date,
    ) -> dict[str, Any] | None:
        result = (
            self.supabase.client.table("premium_daily_selections")
            .select(self.COLUMNS)
            .eq("user_id", user_id)
            .eq("market_day", market_day.isoformat())
            .maybe_single()
            .execute()
        )
        if result is None:
            return None
        return result.data

    def create(
        self,
        *,
        user_id: str,
        market_day: date,
        selection: str,
    ) -> dict[str, Any]:
        try:
            result = (
                self.supabase.client.table("premium_daily_selections")
                .insert(
                    {
                        "user_id": user_id,
                        "market_day": market_day.isoformat(),
                        "selection": selection,
                    }
                )
                .execute()
            )
        except Exception as exc:
            # The database uniqueness constraint is the final authority for
            # concurrent requests. Resolve the persisted row after a conflict.
            existing = self.get(user_id=user_id, market_day=market_day)
            if existing is not None:
                return existing
            raise RuntimeError(
                "Unable to persist the Premium daily selection."
            ) from exc

        if not result.data:
            raise RuntimeError(
                "Supabase did not return the persisted daily selection."
            )
        return result.data[0]


class DailySelectionService:
    def __init__(
        self,
        *,
        repository: DailySelectionRepository | None = None,
        entitlement_service: EntitlementService | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or SupabaseDailySelectionRepository()
        self.entitlements = entitlement_service or EntitlementService()
        self._now_provider = now_provider or (
            lambda: datetime.now(tz=MARKET_TIMEZONE)
        )

    def current_market_day(self) -> date:
        return self._now_provider().astimezone(MARKET_TIMEZONE).date()

    @staticmethod
    def validate_market_day(value: date) -> date:
        if value.weekday() >= 5:
            raise DailySelectionError(
                "Premium daily selections may only be created for a weekday market day."
            )
        return value

    @staticmethod
    def normalize_selection(value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in ALLOWED_SELECTIONS:
            raise DailySelectionError(
                "Selection must be one of: lowest, expected, highest."
            )
        return normalized

    def _authorization(
        self,
        *,
        user_id: str,
        administrator: bool = False,
    ) -> dict[str, Any]:
        try:
            return self.entitlements.authorize_daily_selection(
                user_id=user_id,
                administrator=administrator,
            )
        except EntitlementError as exc:
            raise DailySelectionUnauthorized(str(exc)) from exc

    def get_active(
        self,
        *,
        user_id: str,
        market_day: date | None = None,
        administrator: bool = False,
    ) -> dict[str, Any]:
        day = self.validate_market_day(market_day or self.current_market_day())
        authorization = self._authorization(
            user_id=user_id,
            administrator=administrator,
        )

        if authorization["mode"] == "simultaneous":
            return {
                "mode": "simultaneous",
                "market_day": day,
                "selection": None,
                "locked": False,
                "record": None,
                "available_selections": ["lowest", "expected", "highest"],
            }

        existing = self.repository.get(user_id=user_id, market_day=day)
        return {
            "mode": "locked_selection",
            "market_day": day,
            "selection": existing.get("selection") if existing else None,
            "locked": existing is not None,
            "record": existing,
            "available_selections": ["lowest", "expected", "highest"],
        }

    def select(
        self,
        *,
        user_id: str,
        selection: str,
        market_day: date | None = None,
        administrator: bool = False,
    ) -> dict[str, Any]:
        day = self.validate_market_day(market_day or self.current_market_day())
        normalized = self.normalize_selection(selection)
        authorization = self._authorization(
            user_id=user_id,
            administrator=administrator,
        )

        if authorization["mode"] == "simultaneous":
            return {
                "mode": "simultaneous",
                "market_day": day,
                "selection": None,
                "locked": False,
                "record": None,
                "available_selections": ["lowest", "expected", "highest"],
            }

        existing = self.repository.get(user_id=user_id, market_day=day)
        if existing is not None:
            if existing.get("selection") == normalized:
                return {
                    "mode": "locked_selection",
                    "market_day": day,
                    "selection": normalized,
                    "locked": True,
                    "record": existing,
                    "available_selections": ["lowest", "expected", "highest"],
                }
            raise DailySelectionLocked(existing)

        persisted = self.repository.create(
            user_id=user_id,
            market_day=day,
            selection=normalized,
        )

        if persisted.get("selection") != normalized:
            raise DailySelectionLocked(persisted)

        return {
            "mode": "locked_selection",
            "market_day": day,
            "selection": normalized,
            "locked": True,
            "record": persisted,
            "available_selections": ["lowest", "expected", "highest"],
        }
