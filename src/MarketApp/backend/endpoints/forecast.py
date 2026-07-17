from fastapi import APIRouter, Depends, HTTPException, Query

from schemas.prediction import PredictionRequest
from services.auth_service import (
    AuthenticatedUser,
    get_authenticated_user,
)
from services.entitlement_service import EntitlementError
from services.prediction_service import PredictionService


router = APIRouter()
prediction_service = PredictionService()


@router.get("/supported-horizons")
def get_supported_horizons():
    return {
        "supported_horizons": (
            prediction_service.supported_horizons()
        )
    }


@router.get("/")
async def get_forecast(
    ticker: str = Query(..., min_length=1, max_length=15),
    horizon: int = Query(..., ge=1, le=365),
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return await prediction_service.predict(
            PredictionRequest(
                ticker=ticker,
                horizon=horizon,
            ),
            user_id=user.id,
        )

    except EntitlementError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "message": str(exc),
                "entitlements": exc.entitlements,
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
