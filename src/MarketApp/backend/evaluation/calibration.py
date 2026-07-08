"""
DiMarket probability calibration utilities.

Purpose
-------
Measure and improve how trustworthy model confidence scores are.

Inputs
------
Predicted probabilities and binary actual outcomes.

Outputs
-------
CalibrationMetrics, reliability tables, and calibration comparisons.

Why it matters
--------------
DiMarket should not only predict direction. It should communicate confidence
honestly. If the system says "70% confidence", users should know whether that
confidence level has historically been reliable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


@dataclass(frozen=True)
class CalibrationMetrics:
    brier_score: float
    expected_calibration_error: float
    maximum_calibration_error: float
    average_confidence: float
    empirical_accuracy: float
    sample_count: int
    bin_count: int
    reliability_table: pd.DataFrame

    def to_dict(
        self,
        include_table: bool = False,
    ) -> dict:
        result = asdict(self)

        if include_table:
            result["reliability_table"] = (
                self.reliability_table
                .to_dict(orient="records")
            )
        else:
            result.pop(
                "reliability_table",
                None,
            )

        return result


@dataclass(frozen=True)
class CalibrationComparison:
    split_index: int
    train_samples: int
    test_samples: int
    raw_metrics: CalibrationMetrics
    platt_metrics: CalibrationMetrics
    isotonic_metrics: CalibrationMetrics
    comparison_table: pd.DataFrame


class CalibrationAnalyzer:
    """
    Analyze probability calibration for binary predictions.

    Parameters
    ----------
    probabilities:
        Predicted probability of the positive class.

    actuals:
        Binary actual outcomes where 1 means positive class occurred.

    n_bins:
        Number of reliability bins between 0 and 1.
    """

    def __init__(
        self,
        probabilities: Sequence[float],
        actuals: Sequence[int],
        n_bins: int = 10,
    ) -> None:
        self.probabilities = np.asarray(
            probabilities,
            dtype=float,
        )

        self.actuals = np.asarray(
            actuals,
            dtype=int,
        )

        self.n_bins = int(n_bins)

        self._validate()

    def _validate(self) -> None:
        if self.probabilities.ndim != 1:
            raise ValueError(
                "probabilities must be one-dimensional."
            )

        if self.actuals.ndim != 1:
            raise ValueError(
                "actuals must be one-dimensional."
            )

        if len(self.probabilities) != len(self.actuals):
            raise ValueError(
                "probabilities and actuals must have the same length."
            )

        if self.n_bins <= 0:
            raise ValueError(
                "n_bins must be greater than zero."
            )

        if len(self.probabilities) == 0:
            raise ValueError(
                "At least one probability is required."
            )

        if not np.all(np.isfinite(self.probabilities)):
            raise ValueError(
                "probabilities contains non-finite values."
            )

        if np.any(self.probabilities < 0) or np.any(self.probabilities > 1):
            raise ValueError(
                "probabilities must be between 0 and 1."
            )

        unique_actuals = set(
            np.unique(self.actuals)
        )

        if not unique_actuals.issubset({0, 1}):
            raise ValueError(
                "actuals must contain only 0 and 1."
            )

    def reliability_table(self) -> pd.DataFrame:
        bins = np.linspace(
            0.0,
            1.0,
            self.n_bins + 1,
        )

        rows = []

        for i in range(self.n_bins):
            lower = bins[i]
            upper = bins[i + 1]

            if i == self.n_bins - 1:
                mask = (
                    (self.probabilities >= lower)
                    & (self.probabilities <= upper)
                )
            else:
                mask = (
                    (self.probabilities >= lower)
                    & (self.probabilities < upper)
                )

            count = int(mask.sum())

            if count == 0:
                avg_confidence = np.nan
                empirical_accuracy = np.nan
                calibration_gap = np.nan
            else:
                avg_confidence = float(
                    self.probabilities[mask].mean()
                )

                empirical_accuracy = float(
                    self.actuals[mask].mean()
                )

                calibration_gap = float(
                    empirical_accuracy - avg_confidence
                )

            rows.append(
                {
                    "bin": i + 1,
                    "lower_bound": float(lower),
                    "upper_bound": float(upper),
                    "count": count,
                    "avg_confidence": avg_confidence,
                    "empirical_accuracy": empirical_accuracy,
                    "calibration_gap": calibration_gap,
                    "abs_calibration_gap": (
                        abs(calibration_gap)
                        if not np.isnan(calibration_gap)
                        else np.nan
                    ),
                }
            )

        return pd.DataFrame(rows)

    def expected_calibration_error(
        self,
        table: pd.DataFrame,
    ) -> float:
        total = len(self.probabilities)

        non_empty = table[
            table["count"] > 0
        ]

        if non_empty.empty:
            return 0.0

        weighted_error = (
            non_empty["count"]
            / total
            * non_empty["abs_calibration_gap"]
        ).sum()

        return float(weighted_error)

    @staticmethod
    def maximum_calibration_error(
        table: pd.DataFrame,
    ) -> float:
        non_empty = table[
            table["count"] > 0
        ]

        if non_empty.empty:
            return 0.0

        return float(
            non_empty["abs_calibration_gap"].max()
        )

    def calculate(self) -> CalibrationMetrics:
        table = self.reliability_table()

        brier = float(
            brier_score_loss(
                self.actuals,
                self.probabilities,
            )
        )

        ece = self.expected_calibration_error(
            table
        )

        mce = self.maximum_calibration_error(
            table
        )

        return CalibrationMetrics(
            brier_score=brier,
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
            average_confidence=float(
                self.probabilities.mean()
            ),
            empirical_accuracy=float(
                self.actuals.mean()
            ),
            sample_count=int(
                len(self.probabilities)
            ),
            bin_count=self.n_bins,
            reliability_table=table,
        )


class PlattCalibrator:
    """
    Logistic regression calibration over raw probabilities.
    """

    def __init__(self) -> None:
        self.model = LogisticRegression(
            solver="lbfgs",
        )

    def fit(
        self,
        probabilities,
        actuals,
    ) -> "PlattCalibrator":
        x = _as_feature_matrix(
            probabilities
        )

        y = np.asarray(
            actuals,
            dtype=int,
        )

        self.model.fit(
            x,
            y,
        )

        return self

    def predict(
        self,
        probabilities,
    ) -> np.ndarray:
        x = _as_feature_matrix(
            probabilities
        )

        return self.model.predict_proba(
            x,
        )[:, 1]


class IsotonicCalibrator:
    """
    Non-parametric monotonic probability calibration.
    """

    def __init__(self) -> None:
        self.model = IsotonicRegression(
            out_of_bounds="clip",
        )

    def fit(
        self,
        probabilities,
        actuals,
    ) -> "IsotonicCalibrator":
        x = np.asarray(
            probabilities,
            dtype=float,
        )

        y = np.asarray(
            actuals,
            dtype=int,
        )

        self.model.fit(
            x,
            y,
        )

        return self

    def predict(
        self,
        probabilities,
    ) -> np.ndarray:
        x = np.asarray(
            probabilities,
            dtype=float,
        )

        calibrated = self.model.predict(
            x,
        )

        return np.clip(
            calibrated,
            0.0,
            1.0,
        )


def compare_probability_calibrators(
    probabilities,
    actuals,
    n_bins: int = 10,
    calibration_fraction: float = 0.60,
) -> CalibrationComparison:
    """
    Compare raw, Platt, and isotonic probabilities.

    The first calibration_fraction of samples are used to fit the calibrators.
    The remaining samples are used for evaluation.

    This preserves time order and avoids evaluating calibration on the same
    samples used to fit the calibration model.
    """

    probabilities = np.asarray(
        probabilities,
        dtype=float,
    )

    actuals = np.asarray(
        actuals,
        dtype=int,
    )

    if len(probabilities) != len(actuals):
        raise ValueError(
            "probabilities and actuals must have the same length."
        )

    if len(probabilities) < 20:
        raise ValueError(
            "At least 20 samples are required for calibration comparison."
        )

    split_index = int(
        len(probabilities)
        * calibration_fraction
    )

    split_index = max(
        5,
        min(
            split_index,
            len(probabilities) - 5,
        ),
    )

    train_probs = probabilities[:split_index]
    train_actuals = actuals[:split_index]

    test_probs = probabilities[split_index:]
    test_actuals = actuals[split_index:]

    raw_metrics = CalibrationAnalyzer(
        probabilities=test_probs,
        actuals=test_actuals,
        n_bins=n_bins,
    ).calculate()

    platt = PlattCalibrator().fit(
        train_probs,
        train_actuals,
    )

    platt_probs = platt.predict(
        test_probs,
    )

    platt_metrics = CalibrationAnalyzer(
        probabilities=platt_probs,
        actuals=test_actuals,
        n_bins=n_bins,
    ).calculate()

    isotonic = IsotonicCalibrator().fit(
        train_probs,
        train_actuals,
    )

    isotonic_probs = isotonic.predict(
        test_probs,
    )

    isotonic_metrics = CalibrationAnalyzer(
        probabilities=isotonic_probs,
        actuals=test_actuals,
        n_bins=n_bins,
    ).calculate()

    comparison_table = pd.DataFrame(
        [
            _metrics_row(
                "raw",
                raw_metrics,
            ),
            _metrics_row(
                "platt",
                platt_metrics,
            ),
            _metrics_row(
                "isotonic",
                isotonic_metrics,
            ),
        ]
    )

    return CalibrationComparison(
        split_index=split_index,
        train_samples=len(train_probs),
        test_samples=len(test_probs),
        raw_metrics=raw_metrics,
        platt_metrics=platt_metrics,
        isotonic_metrics=isotonic_metrics,
        comparison_table=comparison_table,
    )


def _as_feature_matrix(
    probabilities,
) -> np.ndarray:
    return np.asarray(
        probabilities,
        dtype=float,
    ).reshape(-1, 1)


def _metrics_row(
    name: str,
    metrics: CalibrationMetrics,
) -> dict:
    return {
        "method": name,
        "samples": metrics.sample_count,
        "avg_confidence": metrics.average_confidence,
        "empirical_accuracy": metrics.empirical_accuracy,
        "brier_score": metrics.brier_score,
        "ece": metrics.expected_calibration_error,
        "mce": metrics.maximum_calibration_error,
    }


def summarize_calibration_metrics(
    metrics: CalibrationMetrics,
) -> str:
    return (
        "\n===================================\n"
        "CONFIDENCE CALIBRATION\n"
        "===================================\n"
        f"Samples              : {metrics.sample_count}\n"
        f"Average Confidence   : {metrics.average_confidence:.2%}\n"
        f"Empirical Accuracy   : {metrics.empirical_accuracy:.2%}\n"
        f"Brier Score          : {metrics.brier_score:.4f}\n"
        f"ECE                  : {metrics.expected_calibration_error:.4f}\n"
        f"MCE                  : {metrics.maximum_calibration_error:.4f}\n"
    )


def summarize_calibration_comparison(
    comparison: CalibrationComparison,
) -> str:
    return (
        "\n===================================\n"
        "CALIBRATION METHOD COMPARISON\n"
        "===================================\n"
        f"Calibration Samples  : {comparison.train_samples}\n"
        f"Evaluation Samples   : {comparison.test_samples}\n"
    )
