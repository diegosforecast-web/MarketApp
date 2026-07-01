from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def get_history(symbol: str):
    # TODO: implement Alpha Vantage-safe history fetch
    return {"symbol": symbol, "message": "history endpoint skeleton"}
