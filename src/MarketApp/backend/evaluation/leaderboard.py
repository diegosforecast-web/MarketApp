from __future__ import annotations

from pathlib import Path

import pandas as pd

from evaluation.reports import load_training_report


def load_reports(report_directory: str):
    """
    Load every *_report.json file in a directory.
    """

    report_directory = Path(report_directory)

    reports = []

    if not report_directory.exists():
        return reports

    for report_file in sorted(
        report_directory.glob("*_report.json")
    ):

        reports.append(
            load_training_report(report_file)
        )

    return reports


def build_leaderboard(
    reports,
    sort_by="mape",
):
    """
    Convert reports into a sortable DataFrame.
    """

    rows = []

    for report in reports:

        metrics = report["metrics"]

        metadata = report["metadata"]

        rows.append(
            {
                "Model": report["model"],
                "Version": report["version"],
                "Training Rows": metadata.get(
                    "training_rows",
                    0,
                ),
                "Validation Rows": metadata.get(
                    "validation_rows",
                    0,
                ),
                "MAE": metrics.get("mae"),
                "RMSE": metrics.get("rmse"),
                "MAPE": metrics.get("mape"),
                "R²": metrics.get("r2"),
                "Directional %": metrics.get(
                    "directional_accuracy"
                ),
                "Bias": metrics.get("bias"),
            }
        )

    if len(rows) == 0:
        return pd.DataFrame()

    leaderboard = pd.DataFrame(rows)

    sort_column = {
        "mae": "MAE",
        "rmse": "RMSE",
        "mape": "MAPE",
        "r2": "R²",
        "directional_accuracy": "Directional %",
        "bias": "Bias",
    }.get(sort_by.lower(), "MAPE")

    ascending = sort_column != "R²"

    return leaderboard.sort_values(
        by=sort_column,
        ascending=ascending,
        ignore_index=True,
    )

def print_leaderboard(df):
    """
    Pretty-print leaderboard.
    """

    if df.empty:

        print("\nNo reports found.")

        return

    print("\n==========================================")
    print("DiMarket Model Leaderboard")
    print("==========================================")

    print(df.to_string(index=False))