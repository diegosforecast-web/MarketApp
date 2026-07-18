"""
Explainability data models.

Purpose
-------
Represent model explanations as typed objects.

Why it matters
--------------
Typed explanation objects can be reused by CLI reports, FastAPI responses,
dashboards, and future AI analyst narratives without rewriting logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    display_name: str
    category: str
    value: float
    impact: float
    direction: str
    description: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PredictionExplanation:
    prediction: str
    confidence: float
    expected_value: float
    top_positive_features: list[FeatureContribution]
    top_negative_features: list[FeatureContribution]
    summary: str

    def to_dict(self) -> dict:
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "top_positive_features": [
                item.to_dict()
                for item in self.top_positive_features
            ],
            "top_negative_features": [
                item.to_dict()
                for item in self.top_negative_features
            ],
            "summary": self.summary,
        }
