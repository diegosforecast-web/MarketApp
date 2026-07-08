import joblib
import pandas as pd

from features.engineered_features import latest_feature_vector


class GBMForecaster:
    def __init__(self, model_path: str):
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.horizon = bundle.get("horizon", 1)
        self.feature_names = bundle.get("feature_names", [])

    def predict(self, price_df: pd.DataFrame) -> float:
        """
        Returns predicted log return.
        """
        x = latest_feature_vector(price_df)

        if self.feature_names:
            x = x[self.feature_names]

        x = pd.DataFrame(
            [x.values],
            columns=x.index,
        )

        predicted_log_return = self.model.predict(x)[0]

        return float(predicted_log_return)

    def predict_expected_return(self, price_df: pd.DataFrame) -> float:
        """
        Returns expected simple return.

        Example:
            0.018 = +1.8%
        """
        log_return = self.predict(price_df)

        return float(pd.Series([log_return]).apply(lambda x: __import__("numpy").exp(x) - 1).iloc[0])