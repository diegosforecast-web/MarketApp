from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


def calculate_metrics(
    y_true,
    y_pred,
    current_close,
):
    """
    Calculate all evaluation metrics used by DiMarket.

    Parameters
    ----------
    y_true : array-like
        Actual future prices.

    y_pred : array-like
        Model predictions.

    current_close : array-like
        Current closing prices used to determine
        prediction direction.

    Returns
    -------
    dict
    """

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    current_close = np.asarray(current_close)

    mae = mean_absolute_error(
        y_true,
        y_pred,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred,
        )
    )

    mape = (
        np.mean(
            np.abs(
                (y_true - y_pred) / y_true
            )
        )
        * 100
    )

    r2 = r2_score(
        y_true,
        y_pred,
    )

    actual_direction = np.sign(
        y_true - current_close
    )

    predicted_direction = np.sign(
        y_pred - current_close
    )

    directional_accuracy = (
        actual_direction == predicted_direction
    ).mean() * 100

    bias = np.mean(
        y_pred - y_true
    )

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape),
        "r2": float(r2),
        "directional_accuracy": float(
            directional_accuracy
        ),
        "bias": float(bias),
    }