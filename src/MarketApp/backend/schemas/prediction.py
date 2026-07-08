from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """
    Request received from the frontend.
    """

    ticker: str = Field(..., min_length=1, max_length=10)
    horizon: int = Field(..., ge=1, le=60)