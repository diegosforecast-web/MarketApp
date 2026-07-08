"""
Model Registry for DiMarket.

Purpose
-------
Centralize model loading, version tracking, and production model selection.

Why it matters
--------------
A trustworthy forecasting platform must know exactly which model is being used,
where it is stored, when it was trained, what metrics it achieved, and which
Git commit produced it.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forecasters.gbm_forecaster import GBMForecaster
from forecasters.direction_forecaster import DirectionForecaster


DEFAULT_REGISTRY = {
    "direction": {
        "production": None,
        "versions": [],
    }
}


class ModelRegistry:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent.parent
        self.models_dir = self.base_dir / "models"
        self.registry_path = self.models_dir / "registry.json"

        self.models_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            self.registry_path.write_text(
                json.dumps(DEFAULT_REGISTRY, indent=4),
                encoding="utf-8",
            )

            return DEFAULT_REGISTRY.copy()

        with self.registry_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def save(self) -> None:
        with self.registry_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.registry,
                file,
                indent=4,
            )

    def register_model(
        self,
        *,
        task: str,
        model_type: str,
        file: str,
        version: str,
        metrics: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        feature_names: list[str] | None = None,
        make_production: bool = True,
        notes: str = "",
    ) -> dict[str, Any]:
        if task not in self.registry:
            self.registry[task] = {
                "production": None,
                "versions": [],
            }

        model_record = {
            "task": task,
            "type": model_type,
            "file": file,
            "version": version,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "git_commit": get_git_commit(),
            "metrics": metrics or {},
            "parameters": parameters or {},
            "feature_names": feature_names or [],
            "notes": notes,
        }

        self.registry[task]["versions"].append(
            model_record,
        )

        if make_production:
            self.registry[task]["production"] = model_record

        self.save()

        return model_record

    def get_model_info(
        self,
        task: str = "direction",
    ) -> dict[str, Any]:
        if task not in self.registry:
            raise KeyError(
                f"No registry entry found for task: {task}"
            )

        production = self.registry[task].get(
            "production",
        )

        if production is None:
            raise ValueError(
                f"No production model registered for task: {task}"
            )

        return production

    def get_model_path(
        self,
        task: str = "direction",
    ) -> Path:
        info = self.get_model_info(
            task,
        )

        return self.models_dir / info["file"]

    def list_versions(
        self,
        task: str = "direction",
    ) -> list[dict[str, Any]]:
        if task not in self.registry:
            return []

        return self.registry[task].get(
            "versions",
            [],
        )

    def load_predictor(
        self,
        task: str = "direction",
    ) -> Any:
        info = self.get_model_info(
            task,
        )

        model_type = info["type"]
        model_path = self.get_model_path(
            task,
        )

        if model_type == "gbm":
            return GBMForecaster(
                str(model_path),
            )
        
        if model_type == "xgboost":
            return DirectionForecaster(
                str(model_path),
            )

        raise ValueError(
            f"Unsupported model type: {model_type}"
        )

    # ------------------------------------------------------------------
    # Backwards compatibility
    # ------------------------------------------------------------------

    def get_predictor(self):
        return self.load_predictor(
            "direction",
        )


def get_git_commit() -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "--short",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    except Exception:
        return None


def next_model_version(
    models_dir: str | Path,
    prefix: str,
    suffix: str = ".pkl",
) -> tuple[str, str]:
    models_dir = Path(models_dir)

    existing = sorted(
        models_dir.glob(
            f"{prefix}_v*{suffix}"
        )
    )

    if not existing:
        version_number = 1
    else:
        latest = existing[-1].stem
        raw_number = latest.split("_v")[-1]
        version_number = int(raw_number) + 1

    version = f"{version_number:03d}"
    filename = f"{prefix}_v{version}{suffix}"

    return version, filename