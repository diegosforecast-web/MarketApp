from fastapi import APIRouter, Depends

from services.auth_service import (
    AuthenticatedUser,
    get_authenticated_user,
)
from services.entitlement_service import EntitlementService
from services.prediction_service import PredictionService


router = APIRouter()
entitlement_service = EntitlementService()
prediction_service = PredictionService()


@router.get("/me")
def get_my_entitlements(
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    return entitlement_service.get_entitlements(
        user_id=user.id,
        supported_horizons=(
            prediction_service.supported_horizons()
        ),
    )
