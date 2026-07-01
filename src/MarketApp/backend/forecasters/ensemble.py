# backend/forecasters/ensemble.py

import pandas as pd

from backend.forecasters.gru_forecaster import GRUForecaster
from backend.forecasters.regime_forecaster import RegimeForecaster
from backend.forecasters.gbm_forecaster import GBMForecaster
from backend.forecasters.linear_forecaster import LinearForecaster
from backend.models.confidence import ConfidenceModel


class EnsembleForecaster:
    """
    Regime-aware ensemble combining:
      - GRU (primary model)
      - GBM (trend-sensitive)
      - Linear (low-variance baseline)

    Horizon is fixed to 1 to match your backend pipeline.
    """

    def __init__(
        self,
        gru_model_path: str,
        regime_model_path: str,
        gbm_model_path: str,
        linear_model_path: str,
    ):
        # Active forecasters
        self.gru = GRUForecaster(gru_model_path, horizon=1)
        self.regime = RegimeForecaster(regime_model_path)
        self.gbm = GBMForecaster(gbm_model_path, horizon=1)
        self.linear = LinearForecaster(linear_model_path, horizon=1)

        # Confidence model
        self.confidence_model = ConfidenceModel()

    def _weights(self, regime_state: int):
        """
        Tailored weights for your GRU-dominant architecture.
        """

        # 0 = normal
        if regime_state == 0:
            return {"gru": 0.55, "gbm": 0.30, "linear": 0.15}

        # 1 = bull
        if regime_state == 1:
            return {"gru": 0.45, "gbm": 0.40, "linear": 0.15}

        # 2 = bear (or stress)
        return {"gru": 0.65, "gbm": 0.25, "linear": 0.10}

    def predict(self, price_df: pd.DataFrame):
        """
        Returns:
            {
                "forecast": float,
                "components": {
                    "gru": float,
                    "gbm": float,
                    "linear": float,
                },
                "regime": int,
                "confidence": {
                    "lower": float,
                    "upper": float,
                    "std": float,
                }
            }
        """

        # Component predictions
        gru_pred = self.gru.predict(price_df)
        gbm_pred = self.gbm.predict(price_df)
        linear_pred = self.linear.predict(price_df)

        # Regime classification
        regime_state = self.regime.predict(price_df)

        components = {
            "gru": float(gru_pred),
            "gbm": float(gbm_pred),
            "linear": float(linear_pred),
        }

        # Regime-aware weights
        w = self._weights(regime_state)

        # Weighted ensemble
        ensemble_pred = (
            w["gru"] * components["gru"]
            + w["gbm"] * components["gbm"]
            + w["linear"] * components["linear"]
        )

        # Confidence intervals
        confidence = self.confidence_model.compute(components)

        return {
            "forecast": float(ensemble_pred),
            "components": components,
            "regime": int(regime_state),
            "confidence": confidence,
        }
