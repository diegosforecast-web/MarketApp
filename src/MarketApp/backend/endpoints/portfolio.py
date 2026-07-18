from fastapi import APIRouter, Depends, HTTPException

from schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    PortfolioAnalyzeRequest,
)
from services.auth_service import (
    AuthenticatedUser,
    get_authenticated_user,
)
from services.portfolio_analysis_service import (
    PortfolioAnalysisService,
)
from services.portfolio_service import PortfolioService


router = APIRouter()
portfolio_service = PortfolioService()
analysis_service = PortfolioAnalysisService()


@router.get("/")
def get_portfolio(
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    return portfolio_service.get_portfolio(
        user_id=user.id,
    )


@router.post("/{portfolio_id}/holdings")
def add_holding(
    portfolio_id: str,
    request: HoldingCreate,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return portfolio_service.add_holding(
            user_id=user.id,
            portfolio_id=portfolio_id,
            ticker=request.ticker,
            shares=request.shares,
            average_cost=request.average_cost,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.patch("/holdings/{holding_id}")
def update_holding(
    holding_id: str,
    request: HoldingUpdate,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return portfolio_service.update_holding(
            user_id=user.id,
            holding_id=holding_id,
            shares=request.shares,
            average_cost=request.average_cost,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.delete("/holdings/{holding_id}")
def delete_holding(
    holding_id: str,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        portfolio_service.delete_holding(
            user_id=user.id,
            holding_id=holding_id,
        )
        return {"deleted": True}
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post("/{portfolio_id}/analyze")
def analyze_portfolio(
    portfolio_id: str,
    request: PortfolioAnalyzeRequest,
    user: AuthenticatedUser = Depends(
        get_authenticated_user
    ),
):
    try:
        return analysis_service.analyze(
            user_id=user.id,
            portfolio_id=portfolio_id,
            horizon=request.horizon,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
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
