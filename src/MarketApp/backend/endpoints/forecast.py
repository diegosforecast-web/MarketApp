from fastapi import APIRouter

from models.gru import GRUModel
from models.tft import TFTModel
from models.gbm import GBMModel
from models.linear import LinearModel
from models.regime import RegimeModel
from models.ensemble import EnsembleModel

router = APIRouter()

# Load models once at startup
gru_model = GRUModel()
tft_model = TFTModel()
gbm_model = GBMModel()
linear_model = LinearModel()
regime_model = RegimeModel()

ensemble_model = EnsembleModel(
    gru_model=gru_model,
    tft_model=tft_model,
    gbm_model=gbm_model,
    linear_model=linear_model,
    regime_model=regime_model,
)

@router.get("/")
def get_forecast(ticker: str, horizon: int = 5, model: str = "ensemble"):
    # TODO: implement model selection logic
    return {
        "ticker": ticker,
        "horizon": horizon,
        "model": model,
        "message": "ML model loader structure ready",
    }
