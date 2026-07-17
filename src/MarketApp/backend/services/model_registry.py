from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forecasters.direction_forecaster import DirectionForecaster
from forecasters.gbm_forecaster import GBMForecaster


class ModelRegistry:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent.parent
        self.models_dir = self.base_dir / "models"
        self.registry_path = self.models_dir / "registry.json"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            self.registry_path.write_text("{}", encoding="utf-8")
            return {}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.registry_path.write_text(
            json.dumps(self.registry, indent=4),
            encoding="utf-8",
        )

    @staticmethod
    def task_for_horizon(task: str, horizon: int) -> str:
        return f"{task}_h{int(horizon)}"

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
        self.registry.setdefault(task, {"production": None, "versions": []})

        record = {
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

        self.registry[task]["versions"].append(record)
        if make_production:
            self.registry[task]["production"] = record

        self.save()
        return record

    def get_model_info(self, task: str) -> dict[str, Any]:
        if task not in self.registry:
            raise KeyError(f"No registry entry found for task: {task}")

        production = self.registry[task].get("production")
        if production is None:
            raise ValueError(f"No production model registered for task: {task}")
        return production

    def get_horizon_model_info(self, task: str, horizon: int) -> dict[str, Any]:
        return self.get_model_info(self.task_for_horizon(task, horizon))

    def list_versions(self, task: str) -> list[dict[str, Any]]:
        return self.registry.get(task, {}).get("versions", [])

    def supported_horizons(self) -> list[int]:
        result: list[int] = []

        for task_name, task_data in self.registry.items():
            if not task_name.startswith("direction_h"):
                continue

            raw = task_name.removeprefix("direction_h")
            if not raw.isdigit() or task_data.get("production") is None:
                continue

            horizon = int(raw)
            return_task = self.task_for_horizon("return_forecast", horizon)
            if self.registry.get(return_task, {}).get("production") is not None:
                result.append(horizon)

        return sorted(set(result))

    def load_predictor(self, task: str):
        info = self.get_model_info(task)
        path = self.models_dir / info["file"]

        if info["type"] == "gbm":
            return GBMForecaster(str(path))
        if info["type"] == "xgboost":
            return DirectionForecaster(str(path))
        raise ValueError(f"Unsupported model type: {info['type']}")

    def load_horizon_predictor(self, task: str, horizon: int):
        task_name = self.task_for_horizon(task, horizon)
        predictor = self.load_predictor(task_name)
        actual = int(getattr(predictor, "horizon", horizon))
        if actual != int(horizon):
            raise RuntimeError(
                f"{task_name} points to a {actual}-day model, not {horizon}."
            )
        return predictor

    def get_predictor(self):
        return self.load_predictor("direction")


def get_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
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
    existing = sorted(models_dir.glob(f"{prefix}_v*{suffix}"))

    version_number = 1
    if existing:
        version_number = int(existing[-1].stem.split("_v")[-1]) + 1

    version = f"{version_number:03d}"
    return version, f"{prefix}_v{version}{suffix}"
