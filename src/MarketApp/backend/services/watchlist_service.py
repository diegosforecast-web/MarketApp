from __future__ import annotations

from typing import Any

from services.supabase_service import SupabaseService


class WatchlistService:
    def __init__(self) -> None:
        self.supabase = SupabaseService()

    def list_for_user(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.client.table("watchlist_items")
            .select("id,user_id,ticker,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )

        return result.data or []

    def add(
        self,
        *,
        user_id: str,
        ticker: str,
    ) -> dict[str, Any]:
        normalized = ticker.strip().upper()

        existing = (
            self.supabase.client.table("watchlist_items")
            .select("id,user_id,ticker,created_at")
            .eq("user_id", user_id)
            .eq("ticker", normalized)
            .limit(1)
            .execute()
        )

        if existing.data:
            return existing.data[0]

        result = (
            self.supabase.client.table("watchlist_items")
            .insert(
                {
                    "user_id": user_id,
                    "ticker": normalized,
                }
            )
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                "Unable to add the ticker to the watchlist."
            )

        return result.data[0]

    def remove(
        self,
        *,
        user_id: str,
        ticker: str,
    ) -> None:
        normalized = ticker.strip().upper()

        result = (
            self.supabase.client.table("watchlist_items")
            .delete()
            .eq("user_id", user_id)
            .eq("ticker", normalized)
            .execute()
        )

        if not result.data:
            raise KeyError("Ticker not found in the watchlist.")
