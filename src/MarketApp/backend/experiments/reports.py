"""
Experiment reporting utilities for DiMarket.

Purpose
-------
Load experiment logs and summarize them as pandas DataFrames.

Why it matters
--------------
DiMarket needs a simple way to compare model runs, calibration quality,
portfolio results, and configuration changes over time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from experiments.tracker import ExperimentTracker


def experiments_to_dataframe(
    output_path: str | Path = "reports/experiments.jsonl",
) -> pd.DataFrame:
    tracker = ExperimentTracker(
        output_path=output_path,
    )

    runs = tracker.load_runs()

    rows: list[dict[str, Any]] = []

    for run in runs:
        row = {
            "run_id": run.run_id,
            "created_at": run.created_at,
            "name": run.name,
            "model_name": run.model_name,
            "dataset": run.dataset,
            "horizon": run.horizon,
            "threshold": run.threshold,
            "git_commit": run.git_commit,
            "notes": run.notes,
        }

        for key, value in run.parameters.items():
            row[f"param_{key}"] = value

        for key, value in run.metrics.items():
            row[f"metric_{key}"] = value

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def print_experiment_summary(
    output_path: str | Path = "reports/experiments.jsonl",
    tail: int = 10,
) -> None:
    df = experiments_to_dataframe(
        output_path=output_path,
    )

    if df.empty:
        print("No experiment runs found.")
        return

    print("\n===================================")
    print("EXPERIMENT SUMMARY")
    print("===================================")

    print(
        df.tail(tail)
        .to_string(index=False)
    )


def export_experiment_summary_csv(
    output_path: str | Path = "reports/experiments.jsonl",
    csv_path: str | Path = "reports/experiment_summary.csv",
) -> Path:
    df = experiments_to_dataframe(
        output_path=output_path,
    )

    csv_path = Path(csv_path)

    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    return csv_path