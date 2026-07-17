from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ensemble.decision_engine import EnsembleDecisionEngine
from services.market_data_service import MarketDataService
from services.portfolio_service import PortfolioService


class PortfolioAnalysisService:
    MAX_HOLDINGS = 12

    def __init__(self) -> None:
        self.portfolios = PortfolioService()
        self.market_data = MarketDataService()
        self.ensemble = EnsembleDecisionEngine()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, value))

    def analyze(
        self,
        *,
        user_id: str,
        portfolio_id: str,
        horizon: int,
    ) -> dict[str, Any]:
        portfolio = self.portfolios.get_portfolio(
            user_id=user_id,
            portfolio_id=portfolio_id,
        )
        holdings = portfolio["holdings"]

        if not holdings:
            raise ValueError("Add at least one holding before analysis.")

        if len(holdings) > self.MAX_HOLDINGS:
            raise ValueError(
                f"Portfolio analysis supports up to {self.MAX_HOLDINGS} "
                "holdings in Version 1."
            )

        supported = self.ensemble.supported_horizons()

        if horizon not in supported:
            raise ValueError(
                f"Unsupported portfolio horizon: {horizon}. "
                f"Available production horizons: {supported}"
            )

        results: list[dict[str, Any]] = []
        total_market_value = 0.0
        weighted_expected_return = 0.0
        weighted_confidence = 0.0
        successful_market_values: list[float] = []

        for holding in holdings:
            ticker = holding["ticker"].upper()

            try:
                history = self.market_data.get_history(ticker)
                current_price = float(history["close"].iloc[-1])
                decision = self.ensemble.predict_point(
                    ticker=ticker,
                    price_df=history,
                    horizon=horizon,
                )

                shares = (
                    float(holding["shares"])
                    if holding.get("shares") is not None
                    else None
                )
                market_value = (
                    current_price * shares
                    if shares is not None
                    else 0.0
                )

                result = {
                    "holding_id": holding["id"],
                    "ticker": ticker,
                    "shares": shares,
                    "average_cost": (
                        float(holding["average_cost"])
                        if holding.get("average_cost") is not None
                        else None
                    ),
                    "current_price": round(current_price, 2),
                    "market_value": round(market_value, 2),
                    "recommendation": decision.recommendation,
                    "confidence": int(
                        round(decision.direction_probability * 100)
                    ),
                    "confidence_level": decision.confidence,
                    "expected_move_pct": round(
                        decision.expected_return * 100,
                        2,
                    ),
                    "forecast_price": round(
                        current_price
                        * (1 + decision.expected_return),
                        2,
                    ),
                    "reasons": decision.reasons,
                    "warnings": decision.warnings,
                    "status": "analyzed",
                }

                results.append(result)
                successful_market_values.append(market_value)
                total_market_value += market_value

            except Exception as exc:
                results.append(
                    {
                        "holding_id": holding["id"],
                        "ticker": ticker,
                        "shares": holding.get("shares"),
                        "average_cost": holding.get("average_cost"),
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        successful = [
            item for item in results
            if item["status"] == "analyzed"
        ]

        if not successful:
            raise RuntimeError(
                "None of the portfolio holdings could be analyzed."
            )

        has_position_sizes = total_market_value > 0

        for item in successful:
            weight = (
                item["market_value"] / total_market_value
                if has_position_sizes
                else 1 / len(successful)
            )
            item["weight_pct"] = round(weight * 100, 2)
            weighted_expected_return += (
                item["expected_move_pct"] * weight
            )
            weighted_confidence += item["confidence"] * weight

        recommendation_distribution = dict(
            Counter(
                item["recommendation"]
                for item in successful
            )
        )

        buy_share = (
            recommendation_distribution.get("BUY", 0)
            / len(successful)
        )
        reject_share = (
            recommendation_distribution.get("REJECT", 0)
            / len(successful)
        )

        opportunity_score = self._clamp(
            50
            + weighted_expected_return * 8
            + (buy_share * 25)
            - (reject_share * 20)
        )

        risk_score = self._clamp(
            50
            - weighted_expected_return * 5
            + (reject_share * 35)
            + max(0, 65 - weighted_confidence) * 0.7
        )

        weights = [item["weight_pct"] / 100 for item in successful]
        concentration = sum(weight * weight for weight in weights)
        diversification_score = self._clamp(
            (1 - concentration) * 125
            if len(weights) > 1
            else 20
        )

        score = self._clamp(
            opportunity_score * 0.45
            + (100 - risk_score) * 0.30
            + weighted_confidence * 0.15
            + diversification_score * 0.10
        )

        ranked = sorted(
            successful,
            key=lambda item: (
                item["recommendation"] == "BUY",
                item["expected_move_pct"],
                item["confidence"],
            ),
            reverse=True,
        )

        riskiest = sorted(
            successful,
            key=lambda item: (
                item["recommendation"] == "REJECT",
                -item["expected_move_pct"],
                100 - item["confidence"],
            ),
            reverse=True,
        )

        strengths: list[str] = []
        risks: list[str] = []

        if buy_share >= 0.5:
            strengths.append(
                "Most analyzed holdings currently carry BUY signals."
            )
        if weighted_confidence >= 70:
            strengths.append(
                "The portfolio has strong average model confidence."
            )
        if weighted_expected_return > 0:
            strengths.append(
                "The weighted expected portfolio move is positive."
            )
        if diversification_score >= 65:
            strengths.append(
                "Position sizing is reasonably diversified."
            )

        if reject_share > 0:
            risks.append(
                f"{recommendation_distribution.get('REJECT', 0)} "
                "holding(s) currently carry REJECT signals."
            )
        if diversification_score < 50:
            risks.append(
                "The portfolio is concentrated in a small number of positions."
            )
        if weighted_confidence < 60:
            risks.append(
                "Average AI confidence is currently below 60%."
            )
        if weighted_expected_return < 0:
            risks.append(
                "The weighted expected portfolio move is negative."
            )

        analysis = {
            "portfolio_id": portfolio["id"],
            "portfolio_name": portfolio["name"],
            "horizon": horizon,
            "score": round(score, 1),
            "opportunity_score": round(opportunity_score, 1),
            "risk_score": round(risk_score, 1),
            "diversification_score": round(diversification_score, 1),
            "expected_return_pct": round(weighted_expected_return, 2),
            "average_confidence": round(weighted_confidence, 1),
            "total_market_value": (
                round(total_market_value, 2)
                if has_position_sizes
                else None
            ),
            "best_opportunity": ranked[0] if ranked else None,
            "highest_risk": riskiest[0] if riskiest else None,
            "recommendation_distribution": {
                "BUY": recommendation_distribution.get("BUY", 0),
                "HOLD": recommendation_distribution.get("HOLD", 0),
                "REJECT": recommendation_distribution.get("REJECT", 0),
            },
            "strengths": strengths,
            "risks": risks,
            "holdings": sorted(
                results,
                key=lambda item: (
                    item.get("status") != "analyzed",
                    -float(item.get("expected_move_pct") or -999),
                ),
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.portfolios.save_analysis(
            user_id=user_id,
            portfolio_id=portfolio["id"],
            analysis=analysis,
        )

        return analysis
