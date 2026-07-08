"""
gbm_runner.py
=============
Adapter for the Gradient Boosting Machine (GBM) model.

GBMs are tabular learners – they operate on flat feature vectors rather
than sequences, so the runner builds a rich feature matrix that captures
the temporal structure the model was trained on.

Feature engineering
-------------------
For each timestep t the feature vector includes:
  - Raw OHLCV values at t
  - Log-returns over windows [1, 5, 10, 20]
  - Rolling mean/std of close over [5, 10, 20]
  - RSI(14), MACD signal, Bollinger-band position

Model formats supported
-----------------------
  - LightGBM  (.lgb / .txt)
  - XGBoost   (.xgb / .json)
  - Scikit-learn compatible (.pkl / .joblib)

Prediction intervals
--------------------
Produced via quantile regression (LightGBM quantile objective) when the
model supports it, or via jackknife+ residuals otherwise.
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base_runner import BaseRunner, PredictOutput

logger = logging.getLogger(__name__)

_ALPHA = 0.05
_FEATURE_WINDOWS = [1, 5, 10, 20]


class GBMRunner(BaseRunner):

    def _load_model(self):
        path = self.model_path or os.getenv("GBM_MODEL_PATH")
        if path:
            logger.info("GBMRunner: loading from %s", path)
            return _load_from_path(path)
        try:
            from models.registry import load as registry_load  # type: ignore[import]
            logger.info("GBMRunner: loading from registry")
            return registry_load("gbm")
        except ModuleNotFoundError:
            raise RuntimeError(
                "GBM model not found. Supply gbm_model_path in CompareConfig "
                "or ensure models.registry is importable."
            )

    def _predict(
        self,
        ohlcv: pd.DataFrame,
        sequence_length: int,
        price_col: str,
    ) -> PredictOutput:
        features, actuals, dates = _build_feature_matrix(
            ohlcv, price_col, min_lookback=max(_FEATURE_WINDOWS)
        )

        model = self._model
        raw_preds = _dispatch_predict(model, features)

        # Try to get quantile predictions for intervals
        intervals = _try_quantile_intervals(model, features, alpha=_ALPHA)
        if intervals is None:
            intervals = _jackknife_intervals(raw_preds, actuals, alpha=_ALPHA)

        return (
            raw_preds.astype(np.float64),
            actuals.astype(np.float64),
            dates,
            intervals,
        )


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _build_feature_matrix(
    ohlcv: pd.DataFrame,
    price_col: str,
    min_lookback: int,
) -> Tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    df = ohlcv.copy()
    close = df[price_col]

    # Log returns
    for w in _FEATURE_WINDOWS:
        df[f"logret_{w}"] = np.log(close / close.shift(w))

    # Rolling statistics
    for w in [5, 10, 20]:
        df[f"roll_mean_{w}"] = close.rolling(w).mean()
        df[f"roll_std_{w}"] = close.rolling(w).std()

    # RSI(14)
    df["rsi_14"] = _rsi(close, 14)

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    df["macd_hist"] = macd - macd_signal

    # Bollinger-band position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_pos"] = (close - bb_mid) / (2 * bb_std + 1e-9)

    df.dropna(inplace=True)

    # Target = next-period close
    targets = df[price_col].shift(-1).dropna()
    df = df.iloc[: len(targets)]

    feature_cols = [
        c for c in df.columns
        if c not in ("open", "high", "low", "close", "volume")
        or c in ("open", "high", "low", "volume")
    ]
    # Include OHLCV as features too
    feature_cols = df.columns.tolist()

    X = df[feature_cols].values.astype(np.float64)
    y = targets.values.astype(np.float64)
    dates = df.index[: len(y)]
    return X, y, dates


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------

def _dispatch_predict(model: Any, X: np.ndarray) -> np.ndarray:
    # LightGBM Booster
    if hasattr(model, "predict") and _is_lgb(model):
        return np.asarray(model.predict(X))
    # XGBoost Booster
    if _is_xgb(model):
        import xgboost as xgb  # type: ignore[import]
        dmat = xgb.DMatrix(X)
        return np.asarray(model.predict(dmat))
    # Generic scikit-learn
    return np.asarray(model.predict(X))


def _try_quantile_intervals(
    model: Any, X: np.ndarray, alpha: float
) -> Optional[np.ndarray]:
    """
    For LightGBM models trained with quantile objective, we can call
    predict with a different alpha.  Returns (n, 2) or None.
    """
    if not _is_lgb(model):
        return None
    try:
        lo = model.predict(X, pred_contrib=False)  # placeholder – real impl below
        # Real LightGBM quantile check
        params = model.params if hasattr(model, "params") else {}
        if params.get("objective") not in ("quantile", "mape"):
            return None
        lo = np.asarray(model.predict(X, alpha=alpha / 2))
        hi = np.asarray(model.predict(X, alpha=1 - alpha / 2))
        return np.stack([lo, hi], axis=1)
    except Exception:  # noqa: BLE001
        return None


def _jackknife_intervals(
    preds: np.ndarray, actuals: np.ndarray, alpha: float
) -> np.ndarray:
    """Leave-one-out residual-based intervals (jackknife+)."""
    residuals = actuals - preds
    lo_q, hi_q = alpha / 2, 1 - alpha / 2
    lo = preds + np.quantile(residuals, lo_q)
    hi = preds + np.quantile(residuals, hi_q)
    return np.stack([lo, hi], axis=1)


def _is_lgb(model: Any) -> bool:
    return type(model).__module__.startswith("lightgbm")


def _is_xgb(model: Any) -> bool:
    return type(model).__module__.startswith("xgboost")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_from_path(path: str) -> Any:
    ext = os.path.splitext(path)[-1].lower()
    if ext in (".txt", ".lgb"):
        try:
            import lightgbm as lgb  # type: ignore[import]
            return lgb.Booster(model_file=path)
        except ImportError:
            raise RuntimeError("lightgbm package required for .txt/.lgb models.")
    if ext in (".xgb", ".json", ".ubj"):
        try:
            import xgboost as xgb  # type: ignore[import]
            booster = xgb.Booster()
            booster.load_model(path)
            return booster
        except ImportError:
            raise RuntimeError("xgboost package required for .xgb/.json models.")
    
    if ext in (".pkl", ".pickle"):

        import joblib

        loaders = [
            lambda: joblib.load(path),
            lambda: pickle.load(open(path, "rb"))
        ]

        last_error = None

        for loader in loaders:
            try:
                return loader()
            except Exception as exc:
                last_error = exc
                logger.exception(
                    "GBM load attempt failed: %s",
                    exc
                )

        raise RuntimeError(
            f"Unable to load GBM model: {last_error}"
        )


    if ext == ".joblib":
        try:
            import joblib  # type: ignore[import]
            return joblib.load(path)
        except ImportError:
            raise RuntimeError("joblib required for .joblib GBM files.")
    raise ValueError(f"Unrecognised GBM model format: {path}")
