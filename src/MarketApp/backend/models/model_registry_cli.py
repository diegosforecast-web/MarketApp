"""
Model Registry CLI for DiMarket.

Usage
-----
python -m models.model_registry_cli list
python -m models.model_registry_cli info direction
"""

from __future__ import annotations

import argparse
from typing import Any

from services.model_registry import ModelRegistry


def format_percent(value: Any) -> str:
    if value is None:
        return "N/A"

    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def print_model_record(record: dict[str, Any]) -> None:
    metrics = record.get("metrics", {})
    parameters = record.get("parameters", {})

    print(f"  Task       : {record.get('task', 'N/A')}")
    print(f"  Version    : {record.get('version', 'N/A')}")
    print(f"  Type       : {record.get('type', 'N/A')}")
    print(f"  File       : {record.get('file', 'N/A')}")
    print(f"  Git Commit : {record.get('git_commit', 'N/A')}")
    print(f"  Registered : {record.get('registered_at', 'N/A')}")

    if parameters:
        print("\n  Parameters")
        print("  ----------")
        for key, value in parameters.items():
            print(f"  {key:<20}: {value}")

    if metrics:
        print("\n  Metrics")
        print("  -------")
        for key, value in metrics.items():
            if key in {"accuracy", "precision", "recall", "f1", "auc", "top10", "top20", "top30"}:
                print(f"  {key:<20}: {format_percent(value)}")
            else:
                print(f"  {key:<20}: {value}")

    notes = record.get("notes", "")
    if notes:
        print("\n  Notes")
        print("  -----")
        print(f"  {notes}")


def list_models() -> None:
    registry = ModelRegistry()

    print("\n===================================")
    print("REGISTERED MODELS")
    print("===================================")

    for task, data in registry.registry.items():
        print(f"\nTask: {task}")
        print("-----------------------------------")

        production = data.get("production")

        if production:
            print("Production:")
            print(f"  Version : {production.get('version', 'N/A')}")
            print(f"  Type    : {production.get('type', 'N/A')}")
            print(f"  File    : {production.get('file', 'N/A')}")
        else:
            print("Production: None")

        versions = data.get("versions", [])

        print("\nVersions:")
        if not versions:
            print("  None")
        else:
            for item in versions:
                print(
                    f"  {item.get('version', 'N/A')} "
                    f"| {item.get('type', 'N/A')} "
                    f"| {item.get('file', 'N/A')}"
                )


def show_info(task: str) -> None:
    registry = ModelRegistry()

    try:
        record = registry.get_model_info(task)
    except Exception as exc:
        print(f"Could not load production model info for task '{task}': {exc}")
        return

    print("\n===================================")
    print(f"MODEL INFO: {task}")
    print("===================================")

    print_model_record(record)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Inspect DiMarket model registry.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "list",
        help="List registered model tasks and versions.",
    )

    info_parser = subparsers.add_parser(
        "info",
        help="Show production model details for a task.",
    )

    info_parser.add_argument(
        "task",
        help="Task name, for example: direction or return_forecast.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "list":
        list_models()
        return

    if args.command == "info":
        show_info(args.task)
        return


if __name__ == "__main__":
    main()