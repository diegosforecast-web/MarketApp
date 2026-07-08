from __future__ import annotations

import numpy as np
import pandas as pd

from evaluation.metrics import calculate_metrics


def persistence_prediction(current_close):
    """
    Persistence baseline.

    Predict tomorrow's close will be today's close.
    """

    return np.asarray(current_close)


def evaluate_persistence(
    current_close,
    actual_close,
):
    """
    Evaluate the persistence benchmark using
    the standard DiMarket metrics.
    """

    predictions = persistence_prediction(current_close)

    metrics = calculate_metrics(
        y_true=actual_close,
        y_pred=predictions,
        current_close=current_close,
    )

    return {
        "model": "Persistence",
        "predictions": predictions,
        "metrics": metrics,
    }


def print_persistence_report(results):
    """
    Pretty-print persistence benchmark results.
    """

    metrics = results["metrics"]

    print("\n==============================")
    print("Persistence Benchmark")
    print("==============================")

    print(f"MAE : {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    print(f"MAPE: {metrics['mape']:.2f}%")
    print(f"R²  : {metrics['r2']:.4f}")
    print(
        f"Directional Accuracy: "
        f"{metrics['directional_accuracy']:.2f}%"
    )
    print(f"Bias: {metrics['bias']:.4f}")