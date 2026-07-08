"""
Experiment tracking data models for DiMarket.

Purpose
-------
Define typed records for training, evaluation, calibration, and portfolio
backtest runs.

Why it matters
--------------
DiMarket needs reproducible experiments. A forecast is only trustworthy if we
can trace which model, dataset, parameters, metrics, and Git commit produced it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class ExperimentRun:
    run_id: str
    created_at: str
    name: str
    model_name: str
    dataset: str
    horizon: int | None = None
    threshold: float | None = None
    git_commit: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @classmethod
    def create(
        cls,
        name: str,
        model_name: str,
        dataset: str,
        horizon: int | None = None,
        threshold: float | None = None,
        git_commit: str | None = None,
        parameters: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        notes: str = "",
    ) -> "ExperimentRun":
        return cls(
            run_id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            name=name,
            model_name=model_name,
            dataset=dataset,
            horizon=horizon,
            threshold=threshold,
            git_commit=git_commit,
            parameters=parameters or {},
            metrics=metrics or {},
            notes=notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)