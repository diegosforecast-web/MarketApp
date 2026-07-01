# backend/models/confidence.py

import numpy as np


class ConfidenceIntervalWrapper:
    """
    Confidence intervals based on model disagreement.
    Tailored to your GRU + GBM + Linear ensemble.
    """

    def __init__(self, min_ratio: float = 0.03):
        """
        min_ratio: minimum CI half-width as % of price (default 3%)
        """
        self.min_ratio = float(min_ratio)

    def compute(self, components: dict):
        """
        components:
            {
                "gru": float,
                "gbm": float,
                "linear": float,
            }

        Returns:
            {
                "lower": float,
                "upper": float,
                "std": float,
            }
        """

        preds = np.array([
            components["gru"],
            components["gbm"],
            components["linear"],
        ], dtype=np.float32)

        mean_pred = float(preds.mean())
        std_pred = float(preds.std())

        # Width from disagreement (1.96 * std)
        width_std = 1.96 * std_pred

        # Minimum width (3% of price)
        width_min = abs(mean_pred) * self.min_ratio

        # Final half-width
        half_width = max(width_std, width_min)

        return {
            "lower": float(mean_pred - half_width),
            "upper": float(mean_pred + half_width),
            "std": float(std_pred),
        }


def ConfidenceModel():
    return ConfidenceIntervalWrapper()
