"""
Data models for the Ensemble Decision Engine.

Purpose
-------
Represent the combined output of DiMarket's production models.

This layer does not train models. It converts model evidence into a clear,
trustworthy decision object.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EnsembleDecision:
    ticker: str
    direction_probability: float
    expected_return: float
    recommendation: str
    confidence: str
    reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)