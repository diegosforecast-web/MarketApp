"""
lstm_runner.py
==============
Adapter that plugs the existing LSTM model into the comparison engine.

The runner is framework-agnostic: it calls ``model.predict()`` which is
the common interface exposed by both Keras/TF and PyTorch wrappers in
MarketApp's model registry.

Integration note
----------------
Set ``lstm_model_path`` in ``CompareConfig`` (or ``LSTM_MODEL_PATH`` env var)
to point at the saved model artefact.  If unset the runner falls back to the
MarketApp model registry (``models.registry.load("lstm")``) so it slots in
with zero config change in most deployments.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .base_runner import BaseRunner, PredictOutput

logger = logging.getLogger(__name__)

_ALPHA = 0.05  # for 95 % prediction interval via bootstrap residuals


class LSTMRunner(BaseRunner):

    def _load_model(self):
        path = self.model_path or os.getenv("LSTM_MODEL_PATH")
        if path:
            logger.info("LSTMRunner: loading model from %s", path)
            return _load_from_path(path)
        # Fall back to the app's model registry
        try:
            from models.registry import load as registry_load  # type: ignore[import]
            logger.info("LSTMRunner: loading model from registry")
            return registry_load("lstm")
        except ModuleNotFoundError:
            raise RuntimeError(
                "LSTM model not found. Supply lstm_model_path in CompareConfig "
                "or ensure models.registry is importable."
            )

    def _predict(
        self,
        ohlcv: pd.DataFrame,
        sequence_length: int,
        price_col: str,
    ) -> PredictOutput:
        prices = ohlcv[price_col].values.astype(np.float64)
        scaled, mn, mx = self._scale(prices)

        X, y = self._build_sequences(scaled, sequence_length)
        raw_preds: np.ndarray = self._model.predict(X, verbose=0).squeeze()

        predictions = self._unscale(raw_preds, mn, mx)
        actuals = self._unscale(y, mn, mx)
        dates = ohlcv.index[sequence_length:]

        intervals = _bootstrap_intervals(raw_preds, actuals, mn, mx, alpha=_ALPHA)

        return predictions, actuals, dates, intervals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_from_path(path: str):
    """Load a Keras/TF saved model or a PyTorch checkpoint wrapper."""
    ext = os.path.splitext(path)[-1].lower()
    if ext in (".h5", ".keras", "") or os.path.isdir(path):
        try:
            import tensorflow as tf  # type: ignore[import]
            return tf.keras.models.load_model(path)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to load LSTM with TF: {exc}") from exc
    raise ValueError(f"Unrecognised LSTM model format: {path}")


def _bootstrap_intervals(
    raw_preds: np.ndarray,
    actuals: np.ndarray,
    mn: float,
    mx: float,
    n_boot: int = 500,
    alpha: float = 0.05,
    rng_seed: int = 42,
) -> np.ndarray:
    """
    Non-parametric bootstrap prediction intervals.
    Returns shape (n, 2) in original price scale.
    """
    rng = np.random.default_rng(rng_seed)
    scaled_actuals = (actuals - mn) / ((mx - mn) or 1.0)
    residuals = scaled_actuals - raw_preds

    lo_q, hi_q = alpha / 2, 1.0 - alpha / 2
    intervals = np.zeros((len(raw_preds), 2))
    for i, pred in enumerate(raw_preds):
        boot_samples = pred + rng.choice(residuals, size=n_boot, replace=True)
        intervals[i, 0] = np.quantile(boot_samples, lo_q)
        intervals[i, 1] = np.quantile(boot_samples, hi_q)

    # Unscale
    intervals = intervals * (mx - mn) + mn
    return intervals
