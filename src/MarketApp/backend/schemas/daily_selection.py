from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


DailySelectionChoice = Literal["lowest", "expected", "highest"]
DailySelectionMode = Literal["locked_selection", "simultaneous"]


class DailySelectionCreate(BaseModel):
    selection: DailySelectionChoice
    market_day: date | None = None

    @field_validator("selection", mode="before")
    @classmethod
    def normalize_selection(cls, value: str) -> str:
        return str(value).strip().lower()


class DailySelectionRecord(BaseModel):
    id: str
    user_id: str
    market_day: date
    selection: DailySelectionChoice
    locked_at: datetime
    created_at: datetime


class DailySelectionResponse(BaseModel):
    mode: DailySelectionMode
    market_day: date
    selection: DailySelectionChoice | None = None
    locked: bool
    record: DailySelectionRecord | None = None
    available_selections: list[DailySelectionChoice] = Field(
        default_factory=lambda: ["lowest", "expected", "highest"]
    )
