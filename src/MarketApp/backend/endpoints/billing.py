from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.auth_service import (
    AuthenticatedUser,
    get_authenticated_user,
)
from services.billing_service import BillingService


router = APIRouter()
billing_service = BillingService()


class CheckoutRequest(BaseModel):
    plan: str


@router.post("/checkout")
def create_checkout(
    request: CheckoutRequest,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return billing_service.create_checkout_session(
            user_id=user.id,
            email=user.email,
            plan=request.plan,
        )
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


@router.post("/portal")
def create_billing_portal(
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return billing_service.create_portal_session(
            user_id=user.id,
        )
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
