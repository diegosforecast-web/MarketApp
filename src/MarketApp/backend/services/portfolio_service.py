from __future__ import annotations

from typing import Any

from services.supabase_service import SupabaseService


class PortfolioService:
    def __init__(self) -> None:
        self.supabase = SupabaseService()

    def get_or_create_default(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        existing = (
            self.supabase.client.table("portfolios")
            .select("id,user_id,name,created_at,updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )

        if existing.data:
            return existing.data[0]

        created = (
            self.supabase.client.table("portfolios")
            .insert(
                {
                    "user_id": user_id,
                    "name": "My Portfolio",
                }
            )
            .execute()
        )

        if not created.data:
            raise RuntimeError("Unable to create the default portfolio.")

        return created.data[0]

    def get_portfolio(
        self,
        *,
        user_id: str,
        portfolio_id: str | None = None,
    ) -> dict[str, Any]:
        portfolio = (
            self.get_or_create_default(user_id=user_id)
            if portfolio_id is None
            else self._get_owned_portfolio(
                user_id=user_id,
                portfolio_id=portfolio_id,
            )
        )

        holdings = (
            self.supabase.client.table("portfolio_holdings")
            .select(
                "id,portfolio_id,ticker,shares,average_cost,"
                "created_at,updated_at"
            )
            .eq("user_id", user_id)
            .eq("portfolio_id", portfolio["id"])
            .order("created_at", desc=False)
            .execute()
        )

        return {
            **portfolio,
            "holdings": holdings.data or [],
        }

    def _get_owned_portfolio(
        self,
        *,
        user_id: str,
        portfolio_id: str,
    ) -> dict[str, Any]:
        result = (
            self.supabase.client.table("portfolios")
            .select("id,user_id,name,created_at,updated_at")
            .eq("id", portfolio_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not result.data:
            raise KeyError("Portfolio not found.")

        return result.data

    def add_holding(
        self,
        *,
        user_id: str,
        portfolio_id: str,
        ticker: str,
        shares: float | None,
        average_cost: float | None,
    ) -> dict[str, Any]:
        self._get_owned_portfolio(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )

        existing = (
            self.supabase.client.table("portfolio_holdings")
            .select("id")
            .eq("portfolio_id", portfolio_id)
            .eq("user_id", user_id)
            .eq("ticker", ticker.upper())
            .limit(1)
            .execute()
        )

        payload = {
            "portfolio_id": portfolio_id,
            "user_id": user_id,
            "ticker": ticker.upper(),
            "shares": shares,
            "average_cost": average_cost,
        }

        if existing.data:
            result = (
                self.supabase.client.table("portfolio_holdings")
                .update(payload)
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            result = (
                self.supabase.client.table("portfolio_holdings")
                .insert(payload)
                .execute()
            )

        if not result.data:
            raise RuntimeError("Unable to save the holding.")

        return result.data[0]

    def update_holding(
        self,
        *,
        user_id: str,
        holding_id: str,
        shares: float | None,
        average_cost: float | None,
    ) -> dict[str, Any]:
        result = (
            self.supabase.client.table("portfolio_holdings")
            .update(
                {
                    "shares": shares,
                    "average_cost": average_cost,
                }
            )
            .eq("id", holding_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise KeyError("Holding not found.")

        return result.data[0]

    def delete_holding(
        self,
        *,
        user_id: str,
        holding_id: str,
    ) -> None:
        result = (
            self.supabase.client.table("portfolio_holdings")
            .delete()
            .eq("id", holding_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise KeyError("Holding not found.")

    def save_analysis(
        self,
        *,
        user_id: str,
        portfolio_id: str,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        result = (
            self.supabase.client.table("portfolio_analyses")
            .insert(
                {
                    "portfolio_id": portfolio_id,
                    "user_id": user_id,
                    "horizon": analysis["horizon"],
                    "score": analysis["score"],
                    "expected_return_pct": analysis[
                        "expected_return_pct"
                    ],
                    "average_confidence": analysis[
                        "average_confidence"
                    ],
                    "response_json": analysis,
                }
            )
            .execute()
        )

        if not result.data:
            raise RuntimeError("Unable to save portfolio analysis.")

        return result.data[0]
