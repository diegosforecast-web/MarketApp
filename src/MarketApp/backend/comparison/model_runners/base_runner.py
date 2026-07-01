"""
base_runner.py
==============
Abstract base class every model runner must implement.

Contract
--------
  predict(ohlcv, sequence_length, price_col)
      -> (predictions, actuals, dates, intervals | None)

  predictions   : np.ndarray shape (n,)   – model's predicted prices
  actuals       : np.ndarray shape (n,)   – ground-truth prices aligned to preds
  dates         : pd.DatetimeIndex (n,)   – timestamps aligned to preds
  intervals     : np.ndarray shape (n, 2) or None  – [lower, upper] CI
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple

import numpy as np
import pandas as pd


PredictOutput = Tuple[
    np.ndarray,           # predictions
    np.ndarray,           # actuals
    pd.DatetimeIndex,     # dates
    Optional[np.ndarray], # prediction intervals [lo, hi]
]


class BaseRunner(ABC):
    """Minimal interface every runner must satisfy."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path
        self._model = None   # lazy-loaded

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def predict(
        self,
        ohlcv: pd.DataFrame,
        sequence_length: int,
        price_col: str,
    ) -> PredictOutput:
        """
        Entry point called by CompareEngine.

        Loads the model on first call (lazy), builds features, runs
        inference, and returns the 4-tuple described above.
        """
        if self._model is None:
            self._model = self._load_model()
        return self._predict(ohlcv, sequence_length, price_col)

    # ------------------------------------------------------------------
    # Abstract helpers (implement in subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    def _load_model(self):
        """Load and return the model object (framework-agnostic)."""

    @abstractmethod
    def _predict(
        self,
        ohlcv: pd.DataFrame,
        sequence_length: int,
        price_col: str,
    ) -> PredictOutput:
        """Run inference and return (predictions, actuals, dates, intervals)."""

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _build_sequences(
        data: np.ndarray, sequence_length: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Slide a window over 1-D ``data`` to build (X, y) pairs.

        X.shape == (n - seq_len, seq_len, 1)
        y.shape == (n - seq_len,)
        """
        X, y = [], []
        for i in range(sequence_length, len(data)):
            X.append(data[i - sequence_length : i])
            y.append(data[i])
        return np.array(X)[..., np.newaxis], np.array(y)

    @staticmethod
    def _scale(arr: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """Min-max scale to [0, 1]. Returns (scaled, min_val, max_val)."""
        mn, mx = arr.min(), arr.max()
        rng = mx - mn if mx != mn else 1.0
        return (arr - mn) / rng, float(mn), float(mx)

    @staticmethod
    def _unscale(arr: np.ndarray, mn: float, mx: float) -> np.ndarray:
        return arr * (mx - mn) + mn
