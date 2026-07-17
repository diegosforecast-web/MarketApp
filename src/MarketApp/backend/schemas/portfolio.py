from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class PortfolioCreate(BaseModel):
    name: str = Field(default="My Portfolio", min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class HoldingCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=15)
    shares: float | None = Field(default=None, gt=0)
    average_cost: float | None = Field(default=None, ge=0)

    @field_validator("ticker")
    @classmethod
    def clean_ticker(cls, value: str) -> str:
        return value.strip().upper()


class HoldingUpdate(BaseModel):
    shares: float | None = Field(default=None, gt=0)
    average_cost: float | None = Field(default=None, ge=0)


class PortfolioAnalyzeRequest(BaseModel):
    horizon: int = Field(default=3, ge=1, le=365)


class PortfolioHoldingResponse(BaseModel):
    id: str
    portfolio_id: str
    ticker: str
    shares: float | None = None
    average_cost: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PortfolioResponse(BaseModel):
    id: str
    name: str
    created_at: str | None = None
    updated_at: str | None = None
    holdings: list[PortfolioHoldingResponse] = Field(default_factory=list)


class PortfolioAnalysisResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str
    horizon: int
    score: float
    opportunity_score: float
    risk_score: float
    diversification_score: float
    expected_return_pct: float
    average_confidence: float
    total_market_value: float | None = None
    best_opportunity: dict[str, Any] | None = None
    highest_risk: dict[str, Any] | None = None
    recommendation_distribution: dict[str, int]
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    holdings: list[dict[str, Any]] = Field(default_factory=list)
    analyzed_at: str
