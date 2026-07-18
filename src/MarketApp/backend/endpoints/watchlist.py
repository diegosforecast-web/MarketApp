from fastapi import APIRouter, Depends, HTTPException

from schemas.watchlist import WatchlistCreate
from services.auth_service import (
    AuthenticatedUser,
    get_authenticated_user,
)
from services.watchlist_service import WatchlistService


router = APIRouter()
watchlist_service = WatchlistService()


@router.get("/")
def get_watchlist(
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    items = watchlist_service.list_for_user(
        user_id=user.id,
    )

    return {
        "items": items,
        "total": len(items),
    }


@router.post("/")
def add_watchlist_item(
    request: WatchlistCreate,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return watchlist_service.add(
            user_id=user.id,
            ticker=request.ticker,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.delete("/{ticker}")
def remove_watchlist_item(
    ticker: str,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        watchlist_service.remove(
            user_id=user.id,
            ticker=ticker,
        )

        return {
            "deleted": True,
            "ticker": ticker.strip().upper(),
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
