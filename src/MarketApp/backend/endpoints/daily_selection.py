from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.daily_selection import (
    DailySelectionCreate,
    DailySelectionResponse,
)
from services.auth_service import AuthenticatedUser, get_authenticated_user
from services.daily_selection_service import (
    DailySelectionError,
    DailySelectionLocked,
    DailySelectionService,
    DailySelectionUnauthorized,
)


router = APIRouter()


def get_daily_selection_service() -> DailySelectionService:
    return DailySelectionService()


@router.get("/", response_model=DailySelectionResponse)
def get_daily_selection(
    market_day: date | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
    service: DailySelectionService = Depends(get_daily_selection_service),
) -> DailySelectionResponse:
    try:
        return DailySelectionResponse.model_validate(
            service.get_active(
                user_id=user.id,
                market_day=market_day,
            )
        )
    except DailySelectionUnauthorized as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DailySelectionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.put("/", response_model=DailySelectionResponse)
def lock_daily_selection(
    request: DailySelectionCreate,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    service: DailySelectionService = Depends(get_daily_selection_service),
) -> DailySelectionResponse:
    try:
        return DailySelectionResponse.model_validate(
            service.select(
                user_id=user.id,
                selection=request.selection,
                market_day=request.market_day,
            )
        )
    except DailySelectionUnauthorized as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DailySelectionLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "existing_selection": exc.existing.get("selection"),
                "market_day": exc.existing.get("market_day"),
            },
        ) from exc
    except DailySelectionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
