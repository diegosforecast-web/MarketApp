from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def run_backtest(ticker: str):
    # TODO: implement backtesting engine
    return {"ticker": ticker, "message": "backtest endpoint skeleton"}
