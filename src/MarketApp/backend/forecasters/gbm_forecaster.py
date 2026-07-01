import joblib
import numpy as np
import pandas as pd

from backend.features.engineered_features import latest_feature_vector

class GBMForecaster:
    def __init__(self, model_path: str):
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.horizon = bundle.get("horizon", 1)

    def predict(self, price_df: pd.DataFrame) -> float:
        """
        price_df: recent OHLCV history, same schema as training.
        Returns predicted future close (horizon steps ahead).
        """
        x = latest_feature_vector(price_df).reshape(1, -1)
        y_pred = self.model.predict(x)[0]
        return float(y_pred)
