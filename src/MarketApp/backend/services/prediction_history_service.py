"""
Prediction history service.

Purpose
-------
Persist forecast responses so DiMarket can show past predictions later.

This is intentionally simple for v1:
- JSONL storage
- one prediction per line
- no database yet
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PredictionHistoryService:
    def __init__(
        self,
        output_path: str | Path = "reports/prediction_history.jsonl",
    ) -> None:
        self.output_path = Path(output_path)

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record(
        self,
        prediction: Any,
    ) -> None:
        if hasattr(
            prediction,
            "model_dump",
        ):
            payload = prediction.model_dump()
        elif hasattr(
            prediction,
            "dict",
        ):
            payload = prediction.dict()
        else:
            payload = dict(prediction)

        payload["recorded_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        with self.output_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    payload,
                    default=str,
                )
                + "\n"
            )