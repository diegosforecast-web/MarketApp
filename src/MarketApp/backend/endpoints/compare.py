from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def compare_models(ticker: str, horizon: int = 5):
    # TODO: implement model comparison logic
    return {
        "ticker": ticker,
        "horizon": horizon,
        "message": "compare_models endpoint skeleton",
    }
