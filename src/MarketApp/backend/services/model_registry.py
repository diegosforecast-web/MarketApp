from pathlib import Path

from forecasters.gbm_forecaster import GBMForecaster


class ModelRegistry:
    """
    Central registry for forecasting models.
    """

    def __init__(self):
        self.models_dir = Path(__file__).resolve().parent.parent / "models"

    def get_predictor(self) -> GBMForecaster:
        model_path = self.models_dir / "gbm_model.pkl"
        return GBMForecaster(str(model_path))