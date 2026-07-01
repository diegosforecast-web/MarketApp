"""
compare_models.py  –  FastAPI route
====================================
POST /compare_models

Orchestrates the full model-comparison pipeline and returns a
frontend-ready JSON payload.

Request body (JSON)
-------------------
{
  "symbol":   "AAPL",              # required – ticker
  "start":    "2024-01-01",        # required – ISO date
  "end":      "2024-12-31",        # required – ISO date
  "models":   ["LSTM","GRU","GBM","Ensemble"],  # optional – subset
  "config":   { ... }              # optional – CompareConfig overrides
}

Response  200 OK
-----------------
{
  "meta":          { ... },
  "ranking":       [ ... ],
  "models":        { ... },
  "chart_data":    { ... },
  "summary_table": [ ... ]
}

Error responses
---------------
  400  –  validation failure (bad symbol, date range, unknown model name)
  500  –  unexpected engine failure (logged server-side)
  503  –  all models failed to produce predictions
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from comparison import CompareEngine
from comparison.compare_engine import CompareConfig
from .dependencies import get_data_loader, get_compare_config_overrides

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compare_models", tags=["Model Comparison"])

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

_VALID_MODELS = {"LSTM", "GRU", "Ensemble", "GBM"}

_VALID_CONFIG_KEYS = {
    "price_column",
    "feature_columns",
    "sequence_length",
    "initial_capital",
    "transaction_cost_bps",
    "risk_free_rate_annual",
    "confidence_level",
    "ranking_weights",
    "lstm_model_path",
    "gru_model_path",
    "ensemble_model_path",
    "gbm_model_path",
}


class CompareRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, examples=["AAPL"])
    start: date = Field(..., examples=["2024-01-01"])
    end: date = Field(..., examples=["2024-12-31"])
    models: Optional[List[str]] = Field(
        default=None,
        description="Subset of models to run. Omit to run all four.",
        examples=[["LSTM", "GRU", "Ensemble", "GBM"]],
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional overrides for CompareConfig fields.",
    )

    # --- Validators --------------------------------------------------------

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        invalid = set(v) - _VALID_MODELS
        if invalid:
            raise ValueError(
                f"Unknown model(s): {invalid}. Valid choices: {_VALID_MODELS}"
            )
        if len(v) == 0:
            raise ValueError("models list must contain at least one entry.")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "CompareRequest":
        if self.start >= self.end:
            raise ValueError("start must be strictly before end.")
        delta = (self.end - self.start).days
        if delta < 30:
            raise ValueError(
                f"Date range too short ({delta} days). Minimum is 30 days."
            )
        if delta > 365 * 10:
            raise ValueError(
                f"Date range too long ({delta} days). Maximum is 10 years."
            )
        return self

    @model_validator(mode="after")
    def validate_config_keys(self) -> "CompareRequest":
        if self.config:
            unknown = set(self.config) - _VALID_CONFIG_KEYS
            if unknown:
                raise ValueError(
                    f"Unknown config key(s): {unknown}. "
                    f"Valid keys: {_VALID_CONFIG_KEYS}"
                )
        return self


class CompareResponse(BaseModel):
    """Thin envelope; actual payload is pass-through JSON."""
    meta: Dict[str, Any]
    ranking: List[Dict[str, Any]]
    models: Dict[str, Any]
    chart_data: Dict[str, Any]
    summary_table: List[Dict[str, Any]]

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Route – POST /compare_models
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CompareResponse,
    response_model_exclude_none=True,
    summary="Compare LSTM, GRU, Ensemble & GBM models",
    description=__doc__,
    status_code=status.HTTP_200_OK,
)
async def compare_models(
    request_body: CompareRequest,
    background_tasks: BackgroundTasks,
    data_loader=Depends(get_data_loader),
    config_overrides: Dict[str, Any] = Depends(get_compare_config_overrides),
) -> JSONResponse:
    """
    Full model-comparison pipeline.

    1. Merge request-level config overrides with server defaults.
    2. Instantiate CompareEngine with the project's data loader.
    3. Run all (or selected) models asynchronously.
    4. Return the serialised comparison payload.
    """
    # ---- Build config -----------------------------------------------------
    try:
        merged_overrides = {**config_overrides, **(request_body.config or {})}
        compare_config = _build_config(merged_overrides)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration: {exc}",
        ) from exc

    # ---- Run engine -------------------------------------------------------
    engine = CompareEngine(config=compare_config, data_loader=data_loader)

    try:
        result = await asyncio.wait_for(
            engine.run(
                symbol=request_body.symbol,
                start=str(request_body.start),
                end=str(request_body.end),
                models=request_body.models,
            ),
            timeout=120.0,  # 2-minute hard ceiling
        )
    except asyncio.TimeoutError:
        logger.error(
            "compare_models timed out for %s %s – %s",
            request_body.symbol, request_body.start, request_body.end,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Comparison timed out. Try a shorter date range or fewer models.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # All models failed
        logger.error("CompareEngine RuntimeError: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error in compare_models for %s", request_body.symbol
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Check server logs.",
        ) from exc

    # ---- Optional: log comparison run in background ----------------------
    background_tasks.add_task(
        _log_comparison_run,
        symbol=request_body.symbol,
        models_run=result["meta"].get("models_run", []),
        ranking=result.get("ranking", []),
    )

    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# GET /compare_models/schema  – surface the request schema for the frontend
# ---------------------------------------------------------------------------

@router.get(
    "/schema",
    summary="Return request schema and valid model names",
    include_in_schema=True,
)
async def compare_models_schema() -> Dict[str, Any]:
    return {
        "valid_models": sorted(_VALID_MODELS),
        "valid_config_keys": sorted(_VALID_CONFIG_KEYS),
        "request_schema": CompareRequest.model_json_schema(),
        "default_config": CompareConfig().__dict__,
    }


# ---------------------------------------------------------------------------
# GET /compare_models/health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary="Health check for the comparison service",
    include_in_schema=False,
)
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "model-comparison"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_config(overrides: Dict[str, Any]) -> CompareConfig:
    """Merge overrides dict into a CompareConfig dataclass instance."""
    base = CompareConfig()
    for key, val in overrides.items():
        if hasattr(base, key):
            setattr(base, key, val)
        else:
            raise ValueError(f"Unknown CompareConfig field: '{key}'")

    # Validate ranking weights sum to a positive number
    weights = base.ranking_weights
    if sum(weights.values()) <= 0:
        raise ValueError("ranking_weights must sum to a positive number.")

    return base


async def _log_comparison_run(
    symbol: str,
    models_run: List[str],
    ranking: List[Dict[str, Any]],
) -> None:
    """Background task: log or persist comparison run metadata."""
    top = ranking[0]["model"] if ranking else "N/A"
    logger.info(
        "Comparison complete | symbol=%s  models=%s  winner=%s",
        symbol, models_run, top,
    )
    # TODO: persist to DB / audit log table
