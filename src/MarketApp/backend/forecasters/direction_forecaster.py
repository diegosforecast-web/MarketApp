import joblib
import pandas as pd

from features.engineered_features import latest_feature_vector
from explainability.shap_engine import ShapEngine


class DirectionForecaster:
    def __init__(self, model_path: str):
        bundle = joblib.load(model_path)

        self.model = bundle["model"]
        self.horizon = bundle.get("horizon", 5)
        self.threshold = bundle.get("threshold", 0.02)
        self.feature_names = bundle.get("feature_names", [])
        self.calibration_method = bundle.get("calibration_method")
        self.calibrator = bundle.get("calibrator")

    def predict_proba(self, price_df: pd.DataFrame) -> float:
        """
        Returns calibrated probability of BUY when a calibrator is available.

        Example:
            0.73 = 73% probability that future return exceeds threshold.
        """
        x = latest_feature_vector(price_df)

        if self.feature_names:
            x = x[self.feature_names]

        x = pd.DataFrame(
            [x.values],
            columns=x.index,
        )

        raw_probability = self.model.predict_proba(x)[0][1]

        if self.calibrator is not None:
            calibrated = self.calibrator.predict(
                [raw_probability]
            )[0]

            return float(calibrated)

        return float(raw_probability)

    def predict(self, price_df: pd.DataFrame) -> int:
        """
        Returns 1 for BUY signal, 0 otherwise.
        """
        probability = self.predict_proba(price_df)

        return int(probability >= 0.50)
    
    def latest_features(self, price_df: pd.DataFrame) -> pd.DataFrame:
        x = latest_feature_vector(price_df)
        if self.feature_names:
            x = x[self.feature_names]

        return pd.DataFrame(
            [x.values],
            columns=x.index,
        )

    def explain(
        self,
        price_df: pd.DataFrame,
        prediction: str,
        confidence: float,
    ):
        x = self.latest_features(price_df)

        engine = ShapEngine(
            self.model,
        )

        return engine.explain_prediction(
            row=x,
            prediction=prediction,
            confidence=confidence,
        )