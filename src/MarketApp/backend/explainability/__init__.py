"""Explainability package for DiMarket."""

from __future__ import annotations

from typing import Any


__all__ = [
    "ExplanationBuilder",
    "FeatureContribution",
    "FeatureDictionary",
    "NarrativeBuilder",
    "PredictionExplanation",
    "ShapEngine",
    "format_explanation_report",
]


def __getattr__(name: str) -> Any:
    if name == "ExplanationBuilder":
        from explainability.explanation import ExplanationBuilder
        return ExplanationBuilder

    if name == "FeatureDictionary":
        from explainability.feature_dictionary import FeatureDictionary
        return FeatureDictionary

    if name in {"FeatureContribution", "PredictionExplanation"}:
        from explainability.models import (
            FeatureContribution,
            PredictionExplanation,
        )
        return {
            "FeatureContribution": FeatureContribution,
            "PredictionExplanation": PredictionExplanation,
        }[name]

    if name == "NarrativeBuilder":
        from explainability.narrative import NarrativeBuilder
        return NarrativeBuilder

    if name == "format_explanation_report":
        from explainability.reporting import format_explanation_report
        return format_explanation_report

    if name == "ShapEngine":
        from explainability.shap_engine import ShapEngine
        return ShapEngine

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
