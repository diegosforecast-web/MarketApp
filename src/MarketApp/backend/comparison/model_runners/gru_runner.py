"""
gru_runner.py
=============
Adapter that plugs the existing GRU model into the comparison engine.

Supports:
- TensorFlow/Keras (.h5, .keras)
- PyTorch state_dict checkpoints (.pt)

Falls back to models.registry.load("gru") if no path is provided.
"""

from __future__ import annotations

import logging
import os

import numpy as np
import pandas as pd

from .base_runner import BaseRunner, PredictOutput

logger = logging.getLogger(__name__)

_MC_PASSES = 50
_ALPHA = 0.05


class GRURunner(BaseRunner):

    def _load_model(self):
        path = self.model_path or os.getenv("GRU_MODEL_PATH")

        if path:
            logger.info("GRURunner: loading model from %s", path)
            return _load_from_path(path)

        try:
            from models.registry import load as registry_load  # type: ignore[import]

            logger.info("GRURunner: loading model from registry")
            return registry_load("gru")

        except ModuleNotFoundError:
            raise RuntimeError(
                "GRU model not found. Supply gru_model_path in CompareConfig "
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

        mc_preds = _mc_dropout_passes(
            self._model,
            X,
            n_passes=_MC_PASSES,
        )

        raw_preds = mc_preds.mean(axis=0)

        predictions = self._unscale(raw_preds, mn, mx)
        actuals = self._unscale(y, mn, mx)

        dates = ohlcv.index[sequence_length:]

        lo = self._unscale(
            np.quantile(mc_preds, _ALPHA / 2, axis=0),
            mn,
            mx,
        )

        hi = self._unscale(
            np.quantile(mc_preds, 1 - _ALPHA / 2, axis=0),
            mn,
            mx,
        )

        intervals = np.stack([lo, hi], axis=1)

        return predictions, actuals, dates, intervals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_from_path(path: str):

    ext = os.path.splitext(path)[-1].lower()

    # ----------------------------------------------------------
    # PyTorch checkpoint
    # ----------------------------------------------------------

    if ext == ".pt":

        try:
            import torch

            from models_to_deploy.gru_model import GRUModel

            model = GRUModel(
                input_size=1,
                hidden_size=64,
                num_layers=2,
                output_size=1,
            )

            state_dict = torch.load(
                path,
                map_location="cpu",
            )

            model.load_state_dict(state_dict)
            model.eval()

            logger.info("Loaded PyTorch GRU checkpoint: %s", path)

            return model

        except Exception as exc:
            raise RuntimeError(
                f"Failed to load GRU PyTorch model: {exc}"
            ) from exc

    # ----------------------------------------------------------
    # TensorFlow / Keras
    # ----------------------------------------------------------

    if ext in (".h5", ".keras", "") or os.path.isdir(path):

        try:
            import tensorflow as tf  # type: ignore[import]

            logger.info("Loaded TensorFlow GRU model: %s", path)

            return tf.keras.models.load_model(path)

        except Exception as exc:
            raise RuntimeError(
                f"Failed to load GRU with TF: {exc}"
            ) from exc

    raise ValueError(f"Unrecognised GRU model format: {path}")


def _mc_dropout_passes(
    model,
    X: np.ndarray,
    n_passes: int,
) -> np.ndarray:
    """
    Supports both TensorFlow and PyTorch models.

    Returns:
        shape (n_passes, n_samples)
    """

    results = []

    for _ in range(n_passes):

        try:
            # TensorFlow path
            out = model(X, training=True)

            if hasattr(out, "numpy"):
                out = out.numpy()

            results.append(np.asarray(out).squeeze())

        except Exception:

            try:
                import torch

                X_tensor = torch.tensor(
                    X,
                    dtype=torch.float32,
                )

                with torch.no_grad():
                    out = model(X_tensor)

                out = out.detach().cpu().numpy().squeeze()

                return np.tile(out, (n_passes, 1))

            except Exception:

                try:
                    det = model.predict(X, verbose=0).squeeze()

                    return np.tile(det, (n_passes, 1))

                except Exception as exc:
                    raise RuntimeError(
                        f"Unable to generate GRU predictions: {exc}"
                    ) from exc

    return np.array(results)
