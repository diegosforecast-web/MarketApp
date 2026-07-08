"""
SHAP engine wrapper.

Purpose
-------
Generate feature-level model explanations while keeping SHAP-specific logic in
one place.

Implementation note
-------------------
For XGBoost models, this module uses the model's native pred_contribs output.
Those values are SHAP-style feature contributions plus a bias term, and they
avoid compatibility issues between SHAP and newer XGBoost base_score formats.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb

from explainability.explanation import ExplanationBuilder
from explainability.feature_dictionary import FeatureDictionary
from explainability.models import (
    FeatureContribution,
    PredictionExplanation,
)
from explainability.narrative import NarrativeBuilder


class ShapEngine:
    def __init__(self, model) -> None:
        self.model = model

    def explain_row(
        self,
        row: pd.DataFrame,
    ) -> tuple[float, list[FeatureContribution]]:
        if not isinstance(row, pd.DataFrame):
            raise TypeError("row must be a pandas DataFrame with one row.")

        if len(row) != 1:
            raise ValueError("row must contain exactly one observation.")

        booster = self.model.get_booster()

        dmatrix = xgb.DMatrix(
            row,
            feature_names=list(row.columns),
        )

        contributions_matrix = booster.predict(
            dmatrix,
            pred_contribs=True,
        )

        contributions_row = np.asarray(
            contributions_matrix,
            dtype=float,
        )[0]

        feature_impacts = contributions_row[:-1]
        expected_value = float(contributions_row[-1])

        contributions = []

        for feature, value, impact in zip(
            row.columns,
            row.iloc[0],
            feature_impacts,
        ):
            impact = float(impact)
            feature = str(feature)

            contributions.append(
                FeatureContribution(
                    feature=feature,
                    display_name=FeatureDictionary.display_name(feature),
                    category=FeatureDictionary.category(feature),
                    value=float(value),
                    impact=impact,
                    direction=NarrativeBuilder.direction_label(impact),
                    description=FeatureDictionary.description(feature),
                )
            )

        return expected_value, contributions

    def explain_prediction(
        self,
        row: pd.DataFrame,
        prediction: str,
        confidence: float,
        top_n: int = 5,
    ) -> PredictionExplanation:
        expected_value, contributions = self.explain_row(row)

        return ExplanationBuilder.build(
            prediction=prediction,
            confidence=confidence,
            expected_value=expected_value,
            contributions=contributions,
            top_n=top_n,
        )
