"""
ensemble_runner.py
==================
Adapter for the Ensemble model in the comparison engine.

The Ensemble combines multiple base learners (e.g. LSTM + GRU + GBM) and
exposes a single unified predict interface.  Two loading strategies:

1. **Pre-trained ensemble artefact** – a serialised object (pickle / joblib)
   that already encapsulates the sub-models and their weights.
2. **Registry delegation** – calls ``models.registry.load("ensemble")``.

Prediction intervals are built from the disagreement between member models
(inter-model standard deviation), which is a natural, interpretable source
of uncertainty for ensemble methods.
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base_runner import BaseRunner, PredictOutput

logger = logging.getLogger(__name__)

_ALPHA = 0.05


class EnsembleRunner(BaseRunner):

    def _load_model(self):
        path = self.model_path or os.getenv("ENSEMBLE_MODEL_PATH")
        if path:
            logger.info("EnsembleRunner: loading from %s", path)
            return _load_from_path(path)
        try:
            from models.registry import load as registry_load  # type: ignore[import]
            logger.info("EnsembleRunner: loading from registry")
            return registry_load("ensemble")
        except ModuleNotFoundError:
            raise RuntimeError(
                "Ensemble model not found. Supply ensemble_model_path in "
                "CompareConfig or ensure models.registry is importable."
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

        # ---- Dispatch to the underlying ensemble object ------------------
        model = self._model
        if _has_member_models(model):
            # Ensemble exposes .members list – collect individual predictions
            member_preds = _collect_member_preds(model, X)
            raw_preds = np.mean(member_preds, axis=0)
            intervals = _member_disagreement_intervals(
                member_preds, mn, mx, alpha=_ALPHA
            )
        elif hasattr(model, "predict"):
            raw_preds = np.asarray(model.predict(X)).squeeze()
            intervals = None
        else:
            raise RuntimeError("Ensemble model exposes neither .members nor .predict()")

        predictions = self._unscale(raw_preds, mn, mx)
        actuals = self._unscale(y, mn, mx)
        dates = ohlcv.index[sequence_length:]

        return predictions, actuals, dates, intervals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_from_path(path: str) -> Any:
    ext = os.path.splitext(path)[-1].lower()
    if ext in (".pkl", ".pickle"):
        with open(path, "rb") as fh:
            return pickle.load(fh)
    if ext in (".joblib",):
        try:
            import joblib  # type: ignore[import]
            return joblib.load(path)
        except ImportError:
            raise RuntimeError("joblib is required to load .joblib ensemble files.")
    # Try Keras last
    try:
        import tensorflow as tf  # type: ignore[import]
        return tf.keras.models.load_model(path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Cannot load ensemble from {path}: {exc}") from exc


def _has_member_models(model: Any) -> bool:
    return hasattr(model, "members") and isinstance(model.members, (list, tuple))


def _collect_member_preds(model: Any, X: np.ndarray) -> np.ndarray:
    """
    Call each member and stack results → shape (n_members, n_samples).
    Members can be Keras models or any object with a .predict() method.
    """
    preds: List[np.ndarray] = []
    for m in model.members:
        try:
            p = m.predict(X, verbose=0)
        except TypeError:
            p = m.predict(X)
        preds.append(np.asarray(p).squeeze())
    return np.vstack(preds)  # (n_members, n_samples)


def _member_disagreement_intervals(
    member_preds: np.ndarray,
    mn: float,
    mx: float,
    alpha: float = 0.05,
) -> np.ndarray:
    """
    Build intervals from quantiles of member-model distributions.
    Returns shape (n_samples, 2) in original price scale.
    """
    lo = np.quantile(member_preds, alpha / 2, axis=0)
    hi = np.quantile(member_preds, 1 - alpha / 2, axis=0)
    lo_unscaled = lo * (mx - mn) + mn
    hi_unscaled = hi * (mx - mn) + mn
    return np.stack([lo_unscaled, hi_unscaled], axis=1)
