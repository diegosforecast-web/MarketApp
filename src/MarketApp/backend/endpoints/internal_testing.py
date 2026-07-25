from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from internal_testing.security import require_internal_admin, require_qa_token
from internal_testing.stripe_test_clock import StripeTestClockService, StripeTestClockUnavailable
from internal_testing.subscription_toolkit import InternalTestingDisabled, SubscriptionTestingToolkit


router = APIRouter(include_in_schema=False)
toolkit = SubscriptionTestingToolkit()
clock_service = StripeTestClockService(toolkit)


class OverrideRequest(BaseModel):
    user_id: str = Field(min_length=1)
    state: Literal["free", "pro", "expired", "trial", "cancelled"]


class SimulationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    event: Literal[
        "new_subscription", "renewal", "cancellation", "expiration",
        "failed_payment", "trial_expiration", "downgrade", "upgrade",
    ]
    plan: Literal["free", "standard", "premium", "gold"] | None = None


class ResetRequest(BaseModel):
    user_id: str | None = None


class QaSessionRequest(BaseModel):
    session_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    state: Literal["free", "pro", "expired", "trial", "cancelled"]


class ClockCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    name: str | None = Field(default=None, max_length=100)


class ClockAdvanceRequest(BaseModel):
    user_id: str = Field(min_length=1)
    clock_id: str = Field(min_length=1)
    frozen_time: int = Field(gt=0)


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InternalTestingDisabled):
        return HTTPException(status_code=404, detail="Not found.")
    if isinstance(exc, StripeTestClockUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Internal testing operation failed.")


@router.put("/override")
def set_override(request: OverrideRequest, actor: str = Depends(require_internal_admin)):
    try:
        return toolkit.set_override(user_id=request.user_id, state=request.state, actor=actor)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.delete("/override/{user_id}")
def clear_override(user_id: str, _: str = Depends(require_internal_admin)):
    try:
        return {"cleared": toolkit.clear_override(user_id=user_id)}
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/simulate")
def simulate(request: SimulationRequest, actor: str = Depends(require_internal_admin)):
    try:
        return toolkit.simulate_event(
            user_id=request.user_id,
            event=request.event,
            plan=request.plan,
            actor=actor,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/qa/session")
def create_qa_session(request: QaSessionRequest, _: str = Depends(require_qa_token)):
    user_id = f"qa:{request.session_id}"
    try:
        snapshot = toolkit.set_override(user_id=user_id, state=request.state, actor="qa-bypass")
        return {
            "authorization": f"QA {request.session_id}",
            "user_id": user_id,
            "snapshot": snapshot,
            "notice": "Synthetic QA identity; no customer account was modified.",
        }
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/reset")
def reset(request: ResetRequest, _: str = Depends(require_internal_admin)):
    try:
        return {"reset": toolkit.reset(user_id=request.user_id)}
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/stripe-test-clock")
def create_test_clock(request: ClockCreateRequest, _: str = Depends(require_internal_admin)):
    try:
        return clock_service.create(user_id=request.user_id, name=request.name)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/stripe-test-clock/advance")
def advance_test_clock(request: ClockAdvanceRequest, _: str = Depends(require_internal_admin)):
    try:
        return clock_service.advance(
            user_id=request.user_id,
            clock_id=request.clock_id,
            frozen_time=request.frozen_time,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
