"""
Experiment tracker for DiMarket.

Purpose
-------
Persist experiment runs to disk in JSON Lines format.

Why it matters
--------------
Terminal output disappears. Experiment records should survive so DiMarket can
compare model runs, calibration quality, portfolio performance, and Git commits
over time.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable

from experiments.models import ExperimentRun


class ExperimentTracker:
    def __init__(
        self,
        output_path: str | Path = "reports/experiments.jsonl",
    ) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def log_run(
        self,
        run: ExperimentRun,
    ) -> None:
        with self.output_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    run.to_dict(),
                    default=str,
                )
                + "\n"
            )

    def load_runs(self) -> list[ExperimentRun]:
        if not self.output_path.exists():
            return []

        runs = []

        with self.output_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                data = json.loads(line)

                runs.append(
                    ExperimentRun(**data)
                )

        return runs

    def latest_run(self) -> ExperimentRun | None:
        runs = self.load_runs()

        if not runs:
            return None

        return runs[-1]


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


def log_experiment(
    *,
    name: str,
    model_name: str,
    dataset: str,
    horizon: int | None = None,
    threshold: float | None = None,
    parameters: dict | None = None,
    metrics: dict | None = None,
    notes: str = "",
    output_path: str | Path = "reports/experiments.jsonl",
) -> ExperimentRun:
    run = ExperimentRun.create(
        name=name,
        model_name=model_name,
        dataset=dataset,
        horizon=horizon,
        threshold=threshold,
        git_commit=get_git_commit(),
        parameters=parameters or {},
        metrics=metrics or {},
        notes=notes,
    )

    tracker = ExperimentTracker(
        output_path=output_path,
    )

    tracker.log_run(run)

    return run