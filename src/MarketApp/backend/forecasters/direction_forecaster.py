import joblib
import pandas as pd

from features.engineered_features import latest_feature_vector


class DirectionForecaster:
    def __init__(self, model_path: str):
        bundle = joblib.load(model_path)

        self.model = bundle["model"]
        self.horizon = bundle.get("horizon", 5)
        self.threshold = bundle.get("threshold", 0.02)
        self.feature_names = bundle.get("feature_names", [])

    def predict_proba(self, price_df: pd.DataFrame) -> float:
        """
        Returns probability of BUY.

        Example:
            0.73 = 73% probability that future return exceeds threshold.
        """
        x = latest_feature_vector(price_df)

        if self.feature_names:
            x = x[self.feature_names]

        x = x.to_numpy().reshape(1, -1)

        probability = self.model.predict_proba(x)[0][1]

        return float(probability)

    def predict(self, price_df: pd.DataFrame) -> int:
        """
        Returns 1 for BUY signal, 0 otherwise.
        """
        probability = self.predict_proba(price_df)

        return int(probability >= 0.50)