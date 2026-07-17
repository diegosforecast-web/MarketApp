from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib

from services.model_registry import ModelRegistry


DIRECTION_REQUIRED_METRICS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
}

RETURN_REQUIRED_METRICS = {
    "mae",
    "rmse",
    "directional_accuracy",
}


def _candidate_for_version(
    registry: ModelRegistry,
    *,
    task: str,
    version: str | None,
) -> dict[str, Any]:
    task_data = registry.registry.get(task)

    if not task_data:
        raise KeyError(f"No registry entry found for task: {task}")

    versions = task_data.get("versions") or []

    if not versions:
        raise ValueError(f"No candidate versions exist for task: {task}")

    if version is None:
        return versions[-1]

    for record in versions:
        if str(record.get("version")) == str(version):
            return record

    raise KeyError(
        f"Version {version} was not found for task {task}."
    )


def _expected_horizon(task: str) -> int:
    marker = "_h"

    if marker not in task:
        raise ValueError(
            "Only horizon-specific tasks can be promoted with this script. "
            "Expected names such as direction_h10 or return_forecast_h10."
        )

    raw = task.rsplit(marker, 1)[-1]

    if not raw.isdigit():
        raise ValueError(f"Unable to parse horizon from task: {task}")

    return int(raw)


def _required_metrics(task: str) -> set[str]:
    if task.startswith("direction_h"):
        return DIRECTION_REQUIRED_METRICS

    if task.startswith("return_forecast_h"):
        return RETURN_REQUIRED_METRICS

    raise ValueError(
        "Task must start with direction_h or return_forecast_h."
    )


def _validate_candidate(
    registry: ModelRegistry,
    *,
    task: str,
    record: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    expected_horizon = _expected_horizon(task)
    file_name = record.get("file")

    if not file_name:
        errors.append("Registry record does not contain a model file.")
        return errors

    model_path = registry.models_dir / str(file_name)

    if not model_path.exists():
        errors.append(f"Model file does not exist: {model_path}")
        return errors

    try:
        bundle = joblib.load(model_path)
    except Exception as exc:
        errors.append(f"Unable to load model bundle: {exc}")
        return errors

    bundle_horizon = int(bundle.get("horizon", -1))
    parameter_horizon = int(
        (record.get("parameters") or {}).get("horizon", -1)
    )

    if bundle_horizon != expected_horizon:
        errors.append(
            "Model bundle horizon mismatch: "
            f"expected {expected_horizon}, found {bundle_horizon}."
        )

    if parameter_horizon != expected_horizon:
        errors.append(
            "Registry parameter horizon mismatch: "
            f"expected {expected_horizon}, found {parameter_horizon}."
        )

    metrics = record.get("metrics") or {}
    missing_metrics = sorted(
        _required_metrics(task) - set(metrics)
    )

    if missing_metrics:
        errors.append(
            "Missing required metrics: "
            + ", ".join(missing_metrics)
        )

    validation_rows = int(
        (record.get("parameters") or {}).get(
            "validation_rows",
            0,
        )
    )

    if validation_rows <= 0:
        errors.append(
            "validation_rows must be greater than zero."
        )

    return errors


def _print_candidate(
    *,
    task: str,
    record: dict[str, Any],
) -> None:
    print("\n===================================")
    print("MODEL CANDIDATE")
    print("===================================")
    print(f"Task       : {task}")
    print(f"Version    : {record.get('version')}")
    print(f"File       : {record.get('file')}")
    print(f"Registered : {record.get('registered_at')}")
    print(f"Git Commit : {record.get('git_commit')}")
    print("\nParameters")
    print(
        json.dumps(
            record.get("parameters") or {},
            indent=2,
        )
    )
    print("\nMetrics")
    print(
        json.dumps(
            record.get("metrics") or {},
            indent=2,
        )
    )


def promote_candidate(
    *,
    task: str,
    version: str | None,
    confirm: bool,
) -> None:
    registry = ModelRegistry()

    record = _candidate_for_version(
        registry,
        task=task,
        version=version,
    )

    _print_candidate(
        task=task,
        record=record,
    )

    errors = _validate_candidate(
        registry,
        task=task,
        record=record,
    )

    if errors:
        print("\nINTEGRITY CHECK: FAILED")

        for error in errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("\nINTEGRITY CHECK: PASSED")
    print(
        "This confirms the artifact and registry metadata are consistent."
    )
    print(
        "It does not replace walk-forward validation or human approval."
    )

    if not confirm:
        print("\nNo production change was made.")
        print(
            "After reviewing the walk-forward results, rerun with --confirm."
        )
        return

    task_data = registry.registry[task]
    previous = task_data.get("production")
    task_data["production"] = record
    registry.save()

    print("\n===================================")
    print("PRODUCTION MODEL UPDATED")
    print("===================================")
    print(f"Task       : {task}")
    print(f"Version    : {record.get('version')}")

    if previous:
        print(f"Previous   : {previous.get('version')}")
    else:
        print("Previous   : none")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and explicitly promote a validated "
            "horizon-specific DiMarket model candidate."
        )
    )

    parser.add_argument(
        "--task",
        required=True,
        help=(
            "Horizon-specific registry task, for example "
            "direction_h10 or return_forecast_h10."
        ),
    )

    parser.add_argument(
        "--version",
        default=None,
        help=(
            "Candidate version to inspect or promote. "
            "Defaults to the newest registered version."
        ),
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help=(
            "Promote the selected candidate after integrity checks. "
            "Use only after reviewing validation results."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    promote_candidate(
        task=args.task,
        version=args.version,
        confirm=args.confirm,
    )
