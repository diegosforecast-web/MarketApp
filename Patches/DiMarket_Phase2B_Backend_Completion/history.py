from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from services.auth_service import AuthenticatedUser, get_authenticated_user
from services.prediction_history_service import PredictionHistoryService


router = APIRouter()
history_service = PredictionHistoryService()


class PredictionVisibilityRequest(BaseModel):
    is_hidden: bool


@router.get("/")
def list_prediction_history(
    limit: int = Query(default=50, ge=1, le=200),
    include_hidden: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    items = history_service.list_for_user(
        user_id=user.id,
        limit=limit,
        verify_due=True,
        include_hidden=include_hidden,
    )
    return {"items": items, "total": len(items)}


@router.get("/stats")
def get_prediction_statistics(
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return history_service.statistics_for_user(user_id=user.id)


@router.post("/verify")
def verify_due_predictions(
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return history_service.verification.verify_due_for_user(
        user_id=user.id,
        limit=limit,
    )


@router.patch("/{prediction_id}/visibility")
def update_prediction_visibility(
    prediction_id: str,
    request: PredictionVisibilityRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    item = history_service.set_visibility(
        user_id=user.id,
        prediction_id=prediction_id,
        is_hidden=request.is_hidden,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found.",
        )

    return item


@router.delete("/{prediction_id}/details")
def delete_completed_prediction_details(
    prediction_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    try:
        item = history_service.purge_details(
            user_id=user.id,
            prediction_id=prediction_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found.",
        )

    return item


@router.post("/{prediction_id}/intraday-check")
def refresh_prediction_intraday(
    prediction_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    try:
        item = history_service.refresh_intraday(
            user_id=user.id,
            prediction_id=prediction_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Intraday market data could not be retrieved "
                "for this prediction."
            ),
        ) from exc

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found.",
        )

    return item


@router.get("/{prediction_id}/progress")
def get_prediction_progress(
    prediction_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    progress = history_service.progress_for_user(
        user_id=user.id,
        prediction_id=prediction_id,
    )

    if progress is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found.",
        )

    return progress


@router.get("/{prediction_id}")
def get_prediction_history_item(
    prediction_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    item = history_service.get_for_user(
        user_id=user.id,
        prediction_id=prediction_id,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found.",
        )

    return item
